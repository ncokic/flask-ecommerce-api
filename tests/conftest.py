from datetime import datetime, UTC, timedelta
from decimal import Decimal
import json
from unittest.mock import MagicMock

import fakeredis
import pytest
from flask_jwt_extended import create_access_token, create_refresh_token
from sqlalchemy import delete, select

from app import create_app
from app.enums import UserRole
from app.extensions import db, limiter, redis_client
from app.models import Product, User, Cart, CartItem, Order, OrderItem, ShippingAddress, Payment, Refund
from app.services import OrderService, CartService, PaymentService
from config import TestingConfig, BASE_DIR


@pytest.fixture(scope="session")
def app():
    app = create_app(config_class=TestingConfig)
    app.redis_client = fakeredis.FakeStrictRedis()
    with app.app_context():
        yield app


@pytest.fixture
def db_session(app):
    with app.app_context():
        db.create_all()
        limiter.storage.reset()
        yield db.session
        db.session.remove()
        db.drop_all()


@pytest.fixture(autouse=True)
def mock_redis():
    server = fakeredis.FakeServer()
    fake_redis = fakeredis.FakeStrictRedis(server=server)

    import app.extensions as extensions
    old_redis = extensions.redis_client
    extensions.redis_client = fake_redis

    yield fake_redis
    extensions.redis_client = old_redis


@pytest.fixture
def client(app, db_session):
    return app.test_client()


@pytest.fixture
def admin_user(app):
    with app.app_context():
        admin = db.session.execute(
            select(User)
            .where(User.email == "admin@test.com")
        ).scalars().first()
        if not admin:
            admin = User(
                username="admin",
                email="admin@test.com",
                role=UserRole.ADMIN,
            )
            admin.password = "admin123"
            db.session.add(admin)
            db.session.commit()
            db.session.refresh(admin)

        access_token = create_access_token(
            identity=admin,
            additional_claims={"role": UserRole.ADMIN.value},
        )
        return {
            "headers": {"Authorization": f"Bearer {access_token}"},
            "id": admin.id,
        }


@pytest.fixture
def test_user(app):
    with app.app_context():
        user = db.session.execute(
            select(User)
            .where(User.email == "user@test.com")
        ).scalars().first()
        if not user:
            user = User(
                username="user",
                email="user@test.com",
                role=UserRole.USER,
            )
            user.password = "user123"
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)

        access_token = create_access_token(
            identity=user,
            additional_claims={"role": UserRole.USER.value},
        )
        refresh_token = create_refresh_token(identity=user)
        return {
            "headers": {"Authorization": f"Bearer {access_token}"},
            "access_token": access_token,
            "refresh_token": refresh_token,
            "id": user.id,
            "email": user.email,
            "username": user.username,
        }



@pytest.fixture
def seed_users(app):
    with app.app_context():
        # users_file = BASE_DIR / "seeds" / "users.json"
        # with open(users_file) as file:
        #     users_data = json.load(file)

        seeded_users = []
        for i in range(1, 16):
            user = User(
                username=f"user_{i}",
                email=f"user{i}@test.com",
                role=UserRole.USER,
            )
            user.password = "user123"
            seeded_users.append(user)
            db.session.add(user)
        db.session.commit()
        yield seeded_users

        db.session.execute(delete(User))
        db.session.commit()


@pytest.fixture
def seed_products(app):
    with app.app_context():
        products_file = BASE_DIR / "seeds" / "products.json"
        with open(products_file) as file:
            products_data = json.load(file)

        seeded_products = []
        for item_data in products_data:
            product = Product(**item_data)
            seeded_products.append(product)
            db.session.add(product)
        db.session.commit()
        yield seeded_products

        db.session.execute(delete(Product))
        db.session.commit()


@pytest.fixture
def seed_cart(app, test_user):
    with app.app_context():
        cart = db.session.execute(
            select(Cart).where(Cart.user_id == test_user["id"])
        ).scalars().first()
        if not cart:
            cart = Cart(user_id=test_user["id"])
            db.session.add(cart)
            db.session.flush()

        cart_items = []
        for i in range(1, 4):
            item = CartItem(
                cart_id=cart.id,
                product_id=i,
                quantity=2,
            )
            cart_items.append(item)
            db.session.add(item)
        db.session.commit()
        db.session.refresh(cart)
        yield cart, cart_items

        db.session.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
        db.session.commit()


@pytest.fixture
def seed_address(app, test_user):
    with app.app_context():
        address = db.session.execute(
            select(ShippingAddress).where(ShippingAddress.street == "Test Street 123")
        ).scalars().first()
        if not address:
            address = ShippingAddress(
                full_name="Test Name",
                street="Test Street 123",
                city="Test City",
                postal_code=12345,
                country="Test Country",
                contact_phone=12345678,
            )
            db.session.add(address)
            db.session.commit()
            db.session.refresh(address)
        yield address

        db.session.execute(
            delete(ShippingAddress).where(ShippingAddress.street == "Test Street 123")
        )
        db.session.commit()


@pytest.fixture
def seed_order(app, test_user, seed_cart, seed_products, seed_address):
    with app.app_context():
        cart, cart_items = seed_cart
        order = db.session.execute(
            select(Order).where(Order.user_id == test_user["id"])
        ).scalars().first()
        if not order:
            order = Order(
                user_id=test_user["id"],
                shipping_address_id=seed_address.id,
                total_amount=Decimal("0.00"),
            )
            db.session.add(order)
            db.session.flush()

        total = Decimal("0.00")
        for item in cart_items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item.product.id,
                price=item.product.price,
                quantity=item.quantity,
            )
            total += item.quantity * item.product.price
            db.session.add(order_item)

        order.total_amount = total

        db.session.commit()
        yield order

        db.session.execute(delete(Order).where(Order.id == order.id))
        db.session.commit()


@pytest.fixture
def seed_orders(app, test_user, seed_address):
    with app.app_context():
        statuses = ["pending", "paid", "processing", "shipped", "delivered", "cancelled"]
        orders = []
        for i in range(1, 13):
            order = Order(
                user_id=test_user["id"],
                shipping_address_id=seed_address.id,
                status=statuses[i % len(statuses)],
                total_amount=Decimal("10.00") * i,
                created_at=datetime.now(UTC)-timedelta(days=i)
            )
            db.session.add(order)
            orders.append(order)
        db.session.commit()
        yield orders

        for order in orders:
            db.session.delete(order)
        db.session.commit()


@pytest.fixture
def seed_payment(app, seed_order):
    with app.app_context():
        payment = db.session.execute(
            select(Payment).where(Payment.order_id == seed_order.id)
        ).scalars().first()
        if not payment:
            payment = Payment(
                order_id=seed_order.id,
                amount=seed_order.total_amount,
            )
            db.session.add(payment)
            db.session.commit()
            db.session.refresh(payment)
        yield payment

        db.session.execute(
            delete(Payment).where(Payment.order_id == seed_order.id)
        )
        db.session.commit()


@pytest.fixture
def seed_refund_request(app, seed_order):
    with app.app_context():
        refund = Refund(
            order_id=seed_order.id,
            reason="not_as_described",
        )
        db.session.add(refund)
        db.session.commit()
        db.session.refresh(refund)
        yield refund

        db.session.delete(refund)
        db.session.commit()


@pytest.fixture
def mock_cart_service():
    mocks = {
        "cart_repo": MagicMock(),
        "cart_item_repo": MagicMock(),
        "product_repo": MagicMock(),
        "order_service": MagicMock(),
        "payment_service": MagicMock(),
        "session": MagicMock(),
    }
    service = CartService(**mocks)
    return service, mocks


@pytest.fixture
def mock_order_service():
    mocks = {
        "order_repo": MagicMock(),
        "order_item_repo":  MagicMock(),
        "address_repo": MagicMock(),
        "payment_service": MagicMock(),
        "refund_repo": MagicMock(),
        "session": MagicMock(),
    }
    service = OrderService(**mocks)
    return service, mocks


@pytest.fixture
def mock_payment_service():
    mocks = {
        "cart_item_repo": MagicMock(),
        "order_repo": MagicMock(),
        "payment_repo": MagicMock(),
        "refund_repo": MagicMock(),
        "session": MagicMock(),
    }
    service = PaymentService(**mocks)
    return service, mocks
