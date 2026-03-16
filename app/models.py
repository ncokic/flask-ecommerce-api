from datetime import datetime, UTC
from decimal import Decimal

from sqlalchemy import Integer, String, Numeric, DateTime, ForeignKey, Enum, UniqueConstraint, Index
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapped_column, Mapped, relationship, declared_attr

from app.enums import UserRole, OrderStatus, PaymentStatus, RefundStatus, RefundReason
from app.extensions import db, bcrypt


class User(db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[int] = mapped_column(String(50), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, values_callable=UserRole.get_enum_values),
        nullable=False,
        default=UserRole.USER,
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    cart: Mapped[Cart] = relationship(back_populates="user")
    orders: Mapped[list[Order]] = relationship(back_populates="user")

    @hybrid_property
    def password(self):
        raise AttributeError("Password is write only")

    @password.setter
    def password(self, plain_password: str):
        self.password_hash = bcrypt.generate_password_hash(plain_password).decode("utf-8")

    def check_password(self, plain_password: str) -> bool:
        return bcrypt.check_password_hash(self.password_hash, plain_password)


class Product(db.Model):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String(250), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, server_default="main")
    price: Mapped[Decimal] = mapped_column(Numeric(10,2), nullable=False)
    stock: Mapped[int] = mapped_column(Integer, nullable=False)


class Cart(db.Model):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    user: Mapped[User] = relationship(back_populates="cart")
    items: Mapped[list[CartItem]] = relationship(back_populates="cart")


class CartItem(db.Model):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    cart: Mapped[Cart] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()


class Order(db.Model):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    shipping_address_id: Mapped[int] = mapped_column(ForeignKey("shipping_addresses.id"))
    billing_address_id: Mapped[int] = mapped_column(ForeignKey("billing_addresses.id"))
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, values_callable=OrderStatus.get_enum_values),
        nullable=False,
        default=OrderStatus.PENDING
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True)
    delivered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    items: Mapped[list[OrderItem]] = relationship(back_populates="order", cascade="all, delete-orphan")
    payments: Mapped[list[Payment]] = relationship(back_populates="order")
    shipping_info: Mapped[ShippingAddress] = relationship(back_populates="order")
    billing_info: Mapped[BillingAddress] = relationship(back_populates="order")
    user: Mapped[User] = relationship(back_populates="orders")
    refund_request: Mapped[Refund] = relationship(back_populates="order")

    __table_args__ = (
        Index("ix_user_id_created_at", "user_id", "created_at"),
    )


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    order: Mapped[Order] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()



class AddressMixin:
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    street: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(30), nullable=False)

    @declared_attr
    def __table_args__(cls):
        return (
            UniqueConstraint(
                "full_name", "street", "city", "postal_code", "country",
                name=f"{cls.__name__.lower()}_full_address"
            ),
        )


class ShippingAddress(AddressMixin, db.Model):
    __tablename__  = "shipping_addresses"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    order: Mapped[list[Order]] = relationship(back_populates="shipping_info")


class BillingAddress(AddressMixin, db.Model):
    __tablename__ = "billing_addresses"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    order: Mapped[list[Order]] = relationship(back_populates="billing_info")


class Payment(db.Model):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer,primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, values_callable=PaymentStatus.get_enum_values),
        nullable=False,
        default=PaymentStatus.PENDING,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False, default="Test")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    order: Mapped[Order] = relationship(back_populates="payments")


class Refund(db.Model):
    __tablename__ = "refund_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    status: Mapped[RefundStatus] = mapped_column(
        Enum(RefundStatus, values_callable=RefundStatus.get_enum_values),
        nullable=False,
        default=RefundStatus.PENDING,
    )
    reason: Mapped[str] = mapped_column(
        Enum(RefundReason, values_callable=RefundReason.get_enum_values),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    order: Mapped[Order] = relationship(back_populates="refund_request")

