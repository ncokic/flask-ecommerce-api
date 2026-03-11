from datetime import datetime, UTC, timedelta, timezone

from sqlalchemy.orm import Session

from app.enums import OrderStatus, PaymentStatus, RefundStatus, RefundReason
from app.repositories import PaymentRepository, OrderRepository, RefundRepository, CartItemRepository
from app.utils.error_handlers import ServiceError

REFUND_WINDOW_DAYS = 7


class PaymentService:
    def __init__(
            self,
            cart_item_repo: CartItemRepository,
            order_repo: OrderRepository,
            payment_repo: PaymentRepository,
            refund_repo: RefundRepository,
            session: Session
    ):
        self.cart_item_repo = cart_item_repo
        self.order_repo = order_repo
        self.payment_repo = payment_repo
        self.refund_repo = refund_repo
        self.session = session


    def get_payment(self, order_id):
        payment = self.payment_repo.get_payment_from_order(order_id)
        if not payment:
            raise ServiceError(404, "Payment not found")
        return payment

    def create_payment(self, order):
        if order.status != OrderStatus.PENDING:
            raise ServiceError(409, "Order payment already processed.")

        payment = self.payment_repo.create_payment(order)
        return payment

    def payment_webhook(self, payment_id, event):
        payment = self.payment_repo.get_by_id(payment_id)
        if not payment:
            raise ServiceError(404, "Payment not found")

        if payment.status != PaymentStatus.PENDING:
            raise ServiceError(409, "Payment already processed.")

        order = payment.order

        if event == "success":
            for item in order.items:
                item.product.stock -= item.quantity
            payment.status = PaymentStatus.ACCEPTED
            payment.order.status = OrderStatus.PAID
            self.cart_item_repo.clear_cart_items(order.user.cart.id)

        elif event == "failure":
            payment.status = PaymentStatus.REJECTED

        payment = self.payment_repo.save(payment)
        self.session.commit()
        self.session.refresh(payment)
        return payment

    def create_refund_request(self, order, reason):
        refund_request = self.refund_repo.create_refund_request(
            order_id=order.id,
            reason=reason,
        )
        if not refund_request:
            raise ServiceError(500, "Service unavailable.")

        self.session.commit()
        self.session.refresh(refund_request)
        return refund_request

    def send_refund_request(self, user_id, order_id, reason):
        order = self.order_repo.get_user_order(user_id, order_id)
        if not order:
            raise ServiceError(404, "Order not found")

        if order.status not in (OrderStatus.SHIPPED, OrderStatus.DELIVERED):
            raise ServiceError(
                409,
                "Order not yet shipped. Use cancel order instead."
            )

        if order.status == OrderStatus.SHIPPED:
            raise ServiceError(
                409,
                "Order has been shipped. Wait for delivery before requesting refund."
            )

        if order.status == OrderStatus.DELIVERED:
            delivered_at = order.delivered_at
            if delivered_at.tzinfo is None:
                delivered_at = delivered_at.replace(tzinfo=timezone.utc)
            if datetime.now(UTC) - delivered_at > timedelta(days=REFUND_WINDOW_DAYS):
                raise ServiceError(409, "Refund window expired.")

        refund_request = self.create_refund_request(order, reason)
        return order


    def handle_refund_request(self, order_id, refund_accepted, order_returned):
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise ServiceError(404, "Order not found.")
        if order.refund_request.status != OrderStatus.PENDING:
            raise ServiceError(409, "Request already processed.")

        if refund_accepted:
            order.refund_request.status = RefundStatus.ACCEPTED
            if order_returned and order.refund_request.reason != RefundReason.DAMAGED_ITEM:
                for item in order.items:
                    item.product.stock += item.quantity
        else:
            order.refund_request.status = RefundStatus.REJECTED

        order.refund_request.processed_at = datetime.now(UTC)
        # send email to user here
        self.session.commit()
        self.session.refresh(order)
        return order