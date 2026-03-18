from sqlalchemy.orm import Session

from app.enums import OrderStatus
from app.repositories import CartRepository, CartItemRepository, ProductRepository
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.utils.error_handlers import ServiceError


class CartService:
    def __init__(
            self,
            cart_repo: CartRepository,
            cart_item_repo: CartItemRepository,
            product_repo: ProductRepository,
            order_service: OrderService,
            payment_service: PaymentService,
            session: Session
    ):
        self.cart_repo = cart_repo
        self.cart_item_repo = cart_item_repo
        self.product_repo = product_repo
        self.order_service = order_service
        self.payment_service = payment_service
        self.session = session
        self.status_code = 200

    def get_or_create_user_cart(self, user_id):
        cart = self.cart_repo.get_cart_by_user_id(user_id)
        if not cart:
            cart = self.cart_repo.create_cart(user_id)
            self.session.commit()
            self.session.refresh(cart)
            self.status_code = 201
        return cart

    def add_item_to_cart(self, user_id, data):
        cart = self.get_or_create_user_cart(user_id)
        product = self.product_repo.get_by_id(data["product_id"])
        if not product:
            raise ServiceError(404, "Product not found")

        cart_item = self.cart_item_repo.find_product_in_cart(cart.id, product.id)
        if cart_item:
            cart_item.quantity += data["quantity"]
        else:
            cart_item = self.cart_item_repo.add_item_to_cart(
                cart_id=cart.id,
                product_id=data["product_id"],
                quantity=data["quantity"],
            )

        self.session.commit()
        self.session.refresh(cart_item)
        cart = self.get_cart_with_totals(user_id)
        return cart_item, cart

    def clear_cart_items(self, user_id):
        cart = self.get_or_create_user_cart(user_id)
        self.cart_item_repo.clear_cart_items(cart.id)
        self.session.commit()
        return self.get_cart_with_totals(user_id)

    def get_cart_item(self, user_id, product_id):
        cart = self.get_cart_with_totals(user_id)
        item = self.cart_item_repo.find_product_in_cart(cart["cart"].id, product_id)
        if not item:
            raise ServiceError(404, "Product not found in cart")
        return item

    def update_cart_item_quantity(self, user_id, product_id, new_quantity):
        item = self.get_cart_item(user_id, product_id)
        if new_quantity == 0:
            self.remove_item(user_id, product_id)
            item = None
        else:
            item.quantity = new_quantity
            self.session.commit()
        cart = self.get_cart_with_totals(user_id)
        return item, cart

    def remove_item(self, user_id, product_id):
        item = self.get_cart_item(user_id, product_id)
        self.cart_item_repo.remove(item)
        self.session.commit()
        return self.get_cart_with_totals(user_id)

    def calculate_totals(self, cart):
        total_items = sum(item.quantity for item in cart.items)
        total_cost = sum(
            item.quantity * item.product.price
            for item in cart.items
        )
        return total_items, total_cost

    def get_cart_with_totals(self, user_id):
        cart = self.get_or_create_user_cart(user_id)
        total_items, total_cost = self.calculate_totals(cart)
        return {
            "cart": cart,
            "total_items": total_items,
            "total_cost": total_cost,
        }

    def checkout_cart(self, user_id, checkout_data):
        cart = self.get_or_create_user_cart(user_id)
        if not cart.items:
            raise ServiceError(422, "You cannot checkout an empty cart.")
        order = self.order_service.create_order(cart, checkout_data)
        if order.status == OrderStatus.REJECTED:
            self.session.commit()
            raise ServiceError(403, "Transaction declined.")
        payment = self.payment_service.create_payment(order)
        self.session.commit()
        self.session.refresh(order)
        return order, payment