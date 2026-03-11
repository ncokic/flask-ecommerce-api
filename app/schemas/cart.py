from marshmallow.fields import List, Nested, Int, Decimal
from marshmallow.validate import Range
from marshmallow_sqlalchemy import auto_field

from app.extensions import ma, db
from app.models import Cart, CartItem
from app.schemas.responses import create_response_schema


class CartBaseSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Cart
        load_instance = True
        sqla_session = db.session
        ordered = True
        exclude = ("user", "created_at",)

    id = auto_field(dump_only=True)
    items = List(Nested("CartItemSchema"))


class CartStructureSchema(ma.Schema):
    cart = Nested(CartBaseSchema)
    total_items = Int(validate=Range(min=0))
    total_cost = Decimal(as_string=True, places=2, validate=Range(min=0))


class CartItemSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = CartItem
        load_instance = True
        sqla_session = db.session
        include_fk = True
        ordered = True
        exclude = ("cart", "cart_id",)

    id = auto_field(dump_only=True)
    product_id = auto_field(load_only=True)
    product = Nested("ProductPublicSchema")
    quantity = auto_field(validate=Range(min=0))


class CartItemCreateSchema(ma.Schema):
    product_id = Int(required=True)
    quantity = Int(required=True, validate=Range(min=1))


class CartItemUpdateSchema(CartItemCreateSchema):
    class Meta:
        exclude = ("product_id",)

    quantity = Int(required=True, validate=Range(min=0))


class CartCheckoutSchema(ma.Schema):
    order = Nested("OrderBaseSchema")
    payment = Nested("PaymentBaseSchema")


class CartSchemas:
    Base = CartBaseSchema
    Cart = CartStructureSchema
    Item = CartItemSchema
    ItemCreate = CartItemCreateSchema
    ItemUpdate = CartItemUpdateSchema
    Checkout = CartCheckoutSchema
    Response = create_response_schema(Cart, name="CartResponseSchema")
    CheckoutResponse = create_response_schema(Checkout, name="CartCheckoutResponseSchema")