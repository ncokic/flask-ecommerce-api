from flask import has_request_context, request
from marshmallow import post_load
from marshmallow.fields import Email, Enum, Str, Nested, List, Int
from marshmallow.validate import Length, OneOf
from marshmallow_sqlalchemy import auto_field

from app.enums import UserRole, UserSortOptions
from app.extensions import ma
from app.models import User
from app.schemas.responses import create_response_schema


class UserAdminSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        load_instance = False
        ordered = True
        exclude=("password_hash",)

    id = auto_field(dump_only=True)
    username = Str(required=True, validate=Length(min=4, max=50))
    email = auto_field(field_class=Email, required=True, validate=Length(min=8, max=100))
    role = Enum(UserRole, by_value=True, dump_only=True)
    cart = Nested("CartBaseSchema", dump_only=True)
    orders = List(Nested("OrderSimplifiedSchema"), dump_only=True)
    created_at = auto_field(dump_only=True)


class UserPublicSchema(UserAdminSchema):
    class Meta(UserAdminSchema.Meta):
        exclude = UserAdminSchema.Meta.exclude + ("role", "cart", "orders")


class UserCreateSchema(UserAdminSchema):
    password = Str(required=True, validate=Length(min=6, max=50), load_only=True)

    @post_load
    def generate_user(self, data, **kwargs):
        password = data.pop("password", None)

        if has_request_context() and request.method == "PATCH":
            if password:
                data["password"] = password
            return data

        user = User(**data)
        if password:
            user.password = password
        return user


class UserSeedSchema(UserCreateSchema):
    role = Enum(UserRole, by_value=True)


class UserUpdateSchema(UserAdminSchema):
    class Meta(UserAdminSchema.Meta):
        exclude = UserAdminSchema.Meta.exclude + ("id", "role",)
        partial = True

    email = Email(validate=Length(min=8, max=100))
    password = Str(validate=Length(min=6, max=50), load_only=True)


class UserLoginSchema(ma.Schema):
    email = Email(required=True)
    password = Str(required=True)


class UserAuthSchema(ma.Schema):
    user = Nested(UserPublicSchema)
    access_token = Str(required=True)
    refresh_token = Str(required=True)


class UserQuerySchema(ma.Schema):
    page = Int(load_default=1)
    per_page = Int(load_default=5)
    search_username = Str()
    search_email = Str()
    sort = Str(validate=OneOf(UserSortOptions.get_enum_values(UserSortOptions)))


class UserSchemas:
    Admin = UserAdminSchema
    Public = UserPublicSchema
    Create = UserCreateSchema
    Seed = UserSeedSchema
    Update = UserUpdateSchema
    Login = UserLoginSchema
    Auth = UserAuthSchema
    Query = UserQuerySchema

    AdminResponse = create_response_schema(Admin, name="UserAdminResponseSchema")
    ListAdminResponse = create_response_schema(Admin, many=True, name="UserListAdminResponseSchema")
    PublicResponse = create_response_schema(Public, name="UserPublicResponseSchema")
    AuthResponse = create_response_schema(Auth, name="UserAuthResponseSchema")
