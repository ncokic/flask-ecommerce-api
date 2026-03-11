from datetime import datetime, timedelta, timezone, UTC
from decimal import Decimal

from sqlalchemy.orm import Session

from app.enums import OrderStatus, RefundStatus, RefundReason
from app.repositories import OrderRepository, OrderItemRepository, ShippingAddressRepository, RefundRepository
from app.services.payment_service import PaymentService
from app.utils.error_handlers import ServiceError

REFUND_WINDOW_MINUTES = 60


class OrderService:
    def __init__(
            self,
            order_repo: OrderRepository,
            order_item_repo: OrderItemRepository,
            address_repo: ShippingAddressRepository,
            payment_service: PaymentService,
            refund_repo: RefundRepository,
            session: Session
    ):
        self.order_repo = order_repo
        self.order_item_repo = order_item_repo
        self.address_repo = address_repo
        self.payment_service = payment_service
        self.refund_repo = refund_repo
        self.session = session


    def query_orders(self, query, page=None, per_page=None, filters=None, sort=None):
        if filters:
            query = self.order_repo.apply_filters(query, filters)

        if sort:
            query = self.order_repo.apply_sorting(query, sort)

        if page and per_page:
            paginated = self.order_repo.paginate_orders(query, page, per_page)
            return paginated.items, paginated.total

        orders = self.order_repo.get_all_orders(query)
        total = len(orders)
        return orders, total

    def list_orders(self, **kwargs):
        query = self.order_repo.select_all()
        return self.query_orders(query, **kwargs)

    def list_user_orders(self, user_id, **kwargs):
        query = self.order_repo.select_user_orders(user_id)
        return self.query_orders(query, **kwargs)

    def get_user_order(self, user_id, order_id):
        order = self.order_repo.get_user_order(user_id, order_id)
        if not order:
            raise ServiceError(404, "Order not found")
        return order

    def change_order_status(self, order_id, new_status):
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise ServiceError(404, "Order not found")

        if order.status == OrderStatus.PAID and new_status == OrderStatus.PROCESSING:
            order.status = OrderStatus.PROCESSING

        elif order.status == OrderStatus.PROCESSING and new_status == OrderStatus.SHIPPED:
            order.status = OrderStatus.SHIPPED

        else:
            raise ServiceError(409, "Invalid order status.")

        self.session.commit()
        self.session.refresh(order)
        return order

    def create_order(self, cart, address):
        existing_address = self.address_repo.get_existing_address(address)
        if existing_address:
            order_address = existing_address
        else:
            order_address = self.address_repo.save(address)
            self.session.flush()

        order = self.order_repo.create_order(cart.user_id)
        order.shipping_address_id = order_address.id
        self.session.flush()

        total_amount = Decimal("0.00")
        for item in cart.items:
            if item.quantity > item.product.stock:
                raise ServiceError(409, f"{item.product.name} is not in stock")
            order_item = self.order_item_repo.add_item_to_order(order, item)
            total_amount += item.quantity * item.product.price
        order.total_amount = total_amount
        return order

    def cancel_order(self, user_id, order_id):
        order = self.get_user_order(user_id, order_id)

        if order.status in (OrderStatus.SHIPPED, OrderStatus.DELIVERED):
            raise ServiceError(
                409,
                "Cancellation failed. Order is already with the courier."
            )

        if order.status == OrderStatus.CANCELLED:
            raise ServiceError(409, "Order already cancelled.")

        #fix for sqlite ignoring timezone=True flag
        created_at = order.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if datetime.now(UTC) - created_at > timedelta(minutes=REFUND_WINDOW_MINUTES):
            raise ServiceError(409, "Cancellation window expired")

        if order.status == OrderStatus.PAID:
            refund_request = self.payment_service.create_refund_request(
                order=order,
                reason=RefundReason.CANCELLED_ORDER,
            )
            refund_request.status = RefundStatus.ACCEPTED
            refund_request.processed_at = datetime.now(UTC)
            for item in order.items:
                item.product.stock += item.quantity

        order.status = OrderStatus.CANCELLED
        self.session.commit()
        self.session.refresh(order)
        return order

    def delivery_webhook(self, order_id):
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise ServiceError(404, "Order not found.")
        if order.status != OrderStatus.SHIPPED:
            raise ServiceError(
                409,
                "Only orders in shipping can be marked as delivered.")
        order.status = OrderStatus.DELIVERED
        order.delivered_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(order)
        return order
