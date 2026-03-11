from marshmallow.fields import Int, Str, Bool, Decimal
from marshmallow.validate import Range, OneOf, Length
from marshmallow_sqlalchemy import auto_field

from app.enums import ProductSortOptions
from app.extensions import ma, db
from app.models import Product
from app.schemas.responses import create_response_schema


class ProductAdminSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Product
        load_instance = True
        sqla_session = db.session
        ordered = True

    id = auto_field(dump_only=True)
    name = auto_field(validate=Length(min=1, max=100))
    description = auto_field()
    category = auto_field()
    price = Decimal(as_string=True, places=2, validate=Range(min=0.01))
    stock = auto_field(validate=Range(min=0))


class ProductPublicSchema(ProductAdminSchema):
    class Meta(ProductAdminSchema.Meta):
        exclude = ("stock",)


class ProductUpdateSchema(ProductAdminSchema):
    class Meta(ProductAdminSchema.Meta):
        load_instance = False


class ProductQuerySchema(ma.Schema):
    page = Int(load_default=1)
    per_page = Int(load_default=5)
    category = Str()
    min_price = Decimal(validate=Range(min=0))
    max_price = Decimal()
    in_stock = Bool()
    search = Str()
    sort = Str(validate=OneOf(ProductSortOptions.get_enum_values(ProductSortOptions)))


class ProductSchemas:
    Admin = ProductAdminSchema
    Public = ProductPublicSchema
    Update = ProductUpdateSchema
    Query = ProductQuerySchema

    AdminResponse = create_response_schema(Admin, name="ProductAdminResponseSchema")
    ListAdminResponse = create_response_schema(Admin, many=True, name="ProductListAdminResponseSchema")
    PublicResponse = create_response_schema(Public, name="ProductPublicResponseSchema")
    ListPublicResponse = create_response_schema(Public, many=True, name="ProductListPublicResponseSchema")