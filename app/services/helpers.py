from app.extensions import db
from app.repositories import (
    ProductRepository,
    UserRepository,
    CartRepository,
    CartItemRepository,
    OrderRepository,
    OrderItemRepository,
    ShippingAddressRepository,
    PaymentRepository,
    RefundRepository, BillingAddressRepository
)
from app.services import ProductService, UserService, CartService, OrderService, PaymentService, FraudService


def get_product_service():
    session = db.session
    repo = ProductRepository(session)
    return ProductService(repo, session)

def get_user_service():
    session = db.session
    repo = UserRepository(session)
    return UserService(repo, session)

def get_cart_service():
    session = db.session
    return CartService(
        cart_repo=CartRepository(session),
        cart_item_repo=CartItemRepository(session),
        product_repo=ProductRepository(session),
        order_service=get_order_service(),
        payment_service=get_payment_service(),
        session=session,
    )

def get_order_service():
    session = db.session
    return OrderService(
        order_repo=OrderRepository(session),
        order_item_repo=OrderItemRepository(session),
        ship_address_repo=ShippingAddressRepository(session),
        bill_address_repo=BillingAddressRepository(session),
        payment_service=get_payment_service(),
        fraud_service=get_fraud_service(),
        refund_repo=RefundRepository(session),
        session=session,
    )

def get_payment_service():
    session = db.session
    return PaymentService(
        cart_item_repo=CartItemRepository(session),
        order_repo=OrderRepository(session),
        payment_repo=PaymentRepository(session),
        refund_repo=RefundRepository(session),
        session=session,
    )

def get_fraud_service():
    return FraudService(order_repo=OrderRepository(db.session))

def split_query_args(args):
    page = args.pop("page", None)
    per_page = args.pop("per_page", None)
    sort = args.pop("sort", None)
    return page, per_page, args, sort