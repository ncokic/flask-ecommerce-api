import re

from marshmallow.fields import Nested, List, Decimal, Int, Str, Enum, Bool
from marshmallow.validate import Range, OneOf, Length, Regexp
from marshmallow_sqlalchemy import auto_field

from app.enums import OrderSortOptions, OrderStatus, RefundStatus
from app.extensions import ma, db
from app.models import Order, OrderItem, ShippingAddress, BillingAddress
from app.schemas.responses import create_response_schema


class OrderBaseSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Order
        load_instance = True
        sqla_session = db.session
        include_fk = True
        ordered = True
        exclude = ("payments", "user",)

    id = auto_field(dump_only=True)
    user_id = auto_field(dump_only=True)
    shipping_address_id = auto_field(dump_only=True)
    billing_address_id = auto_field(dump_only=True)
    status = Enum(OrderStatus, by_value=True, dump_only=True)
    total_amount = Decimal(as_string=True, places=2, validate=Range(min=0))
    created_at = auto_field(dump_only=True)
    delivered_at = auto_field(dump_only=True)
    items = List(Nested("OrderItemSchema"))
    shipping_info = Nested("ShippingAddressSchema")
    billing_info = Nested("BillingAddressSchema")
    refund_request = Nested("RefundSchema")


class OrderSimplifiedSchema(OrderBaseSchema):
    class Meta(OrderBaseSchema.Meta):
        fields = ("user_id", "status", "refund_request",)
        exclude = ()


class OrderStatusSchema(OrderBaseSchema):
    class Meta(OrderBaseSchema.Meta):
        fields = ("status",)
        exclude = ()

    status = Enum(OrderStatus, by_value=True)

class OrderQuerySchema(ma.Schema):
    page = Int(load_default=1)
    per_page = Int(load_default=5)
    status = Str()
    min_amount = Decimal(validate=Range(min=0))
    max_amount = Decimal()
    sort = Str(validate=OneOf(OrderSortOptions.get_enum_values(OrderSortOptions)))


class OrderAdminQuerySchema(OrderQuerySchema):
    user_id = Int()
    refund_status = Str(validate=OneOf(RefundStatus.get_enum_values(RefundStatus)))


class OrderItemSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = OrderItem
        load_instance = True
        sqla_session = db.session
        include_fk = True
        ordered = True
        exclude = ("product_id", "order",)

    id = auto_field(dump_only=True)
    order_id = auto_field(load_only=True)
    price = Decimal(as_string=True, places=2, validate=Range(min=0))
    quantity = auto_field(validate=Range(min=0))
    product = Nested("ProductPublicSchema")


class ShippingAddressSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ShippingAddress
        include_fk = True
        ordered = True

    id = auto_field(dump_only=True)
    full_name = auto_field(validate=Length(min=1, max=100))
    street = auto_field(validate=Length(min=1, max=100))
    city = auto_field(validate=Length(min=1, max=100))
    postal_code = auto_field(validate=[
        Length(min=3, max=10),
        Regexp(r"^[A-Z0-9\s-]+$", flags=re.I, error="Invalid postal code format.")
    ])
    country = auto_field(validate=Length(min=1, max=100))
    contact_phone = auto_field(validate=[
        Regexp(r"^\+?[0-9\s-]{7,20}$", error="Invalid phone number format.")
    ])


class BillingAddressSchema(ShippingAddressSchema):
    class Meta:
        model = BillingAddress


class AddressCreateSchema(ma.Schema):
    shipping_address = Nested(ShippingAddressSchema, required=True)
    billing_same_as_shipping = Bool(load_default=True)
    billing_address = Nested(BillingAddressSchema, allow_none=True)


class OrderWebhookCreateSchema(ma.Schema):
    order_id = Int(required=True, validate=Range(min=1))


class OrderDeliverySchema(OrderBaseSchema):
    class Meta(OrderBaseSchema.Meta):
        fields = ("status", "delivered_at",)
        exclude = ()


class OrderReviewFraudSchema(ma.Schema):
    action = Str(required=True, validate=OneOf(["approve", "reject"]))


class OrderSchemas:
    Base = OrderBaseSchema
    Simplified = OrderSimplifiedSchema
    Status = OrderStatusSchema
    ReviewFraud = OrderReviewFraudSchema
    Delivery = OrderDeliverySchema
    Query = OrderQuerySchema
    AdminQuery = OrderAdminQuerySchema
    Item = OrderItemSchema
    AddressCreate = AddressCreateSchema
    WebhookCreate = OrderWebhookCreateSchema

    Response = create_response_schema(Base, name="OrderResponseSchema")
    ListResponse = create_response_schema(Base, many=True, name="OrderListResponseSchema")
    WebhookResponse = create_response_schema(Delivery, name="OrderWebhookResponseSchema")