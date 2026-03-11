from marshmallow.fields import Nested, Int, Str, Decimal, Enum, Bool
from marshmallow.validate import Range, OneOf
from marshmallow_sqlalchemy import auto_field

from app.enums import PaymentStatus, RefundReason, RefundStatus
from app.extensions import ma, db
from app.models import Payment, Refund
from app.schemas.responses import create_response_schema


class PaymentBaseSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Payment
        load_instance = True
        sqla_session = db.session
        ordered = True

    id = auto_field(dump_only=True)
    status = Enum(PaymentStatus, by_value=True, dump_only=True)
    amount = Decimal(as_string=True, places=2, validate=Range(min=0))
    provider = auto_field(dump_only=True)
    created_at = auto_field(dump_only=True)
    order = Nested("OrderSimplifiedSchema")


class PaymentStatusSchema(PaymentBaseSchema):
    class Meta(PaymentBaseSchema.Meta):
        fields = ("status",)


class PaymentWebhookCreateSchema(ma.Schema):
    payment_id = Int(required=True, validate=Range(min=1))
    event = Str(required=True, validate=OneOf(["success", "failure"]))


class PaymentWebhookStatusSchema(ma.Schema):
    order_status = Nested("OrderStatusSchema")
    payment_status = Nested(PaymentStatusSchema)


class RefundSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Refund
        load_instance = True
        sqla_session = db.session
        include_fk = True
        ordered = True

    id = auto_field(dump_only=True)
    order_id = auto_field(dump_only=True)
    status = Enum(RefundStatus, by_value=True, dump_only=True)
    reason = Enum(RefundReason, by_value=True, dump_only=True)
    created_at = auto_field(dump_only=True)
    processed_at = auto_field(dump_only=True)


class RefundRequestSchema(ma.Schema):
    reason = Str(
        required=True,
        validate=OneOf(RefundReason.get_enum_values(RefundReason)),
    )


class RefundReviewSchema(ma.Schema):
    accepted = Bool(required=True)
    order_returned = Bool(required=True)


class PaymentSchemas:
    Base = PaymentBaseSchema
    Status = PaymentStatusSchema
    WebhookCreate = PaymentWebhookCreateSchema
    WebhookStatus = PaymentWebhookStatusSchema
    Refund = RefundSchema
    RefundRequest = RefundRequestSchema
    RefundReview = RefundReviewSchema

    Response = create_response_schema(Base, name="PaymentResponseSchema")
    WebhookResponse = create_response_schema(WebhookStatus, name="PaymentWebhookResponseSchema")
