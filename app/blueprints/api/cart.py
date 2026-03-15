from flask_jwt_extended import jwt_required, current_user
from flask_smorest import Blueprint

from app.extensions import limiter
from app.schemas.cart import CartSchemas
from app.schemas.orders import OrderSchemas
from app.schemas.payments import PaymentSchemas
from app.services.helpers import get_cart_service
from app.utils.responses import api_response
from app.utils.security import idempotent_route

api_cart_bp = Blueprint(
    "api_cart",
    __name__,
    url_prefix="/api/cart",
    description="Cart management endpoints",
)


@api_cart_bp.route("")
@jwt_required()
@api_cart_bp.response(200, CartSchemas.Response)
@api_cart_bp.alt_response(201, schema=CartSchemas.Response)
def view_cart():
    """Retrieve the current user's cart and its items."""
    service = get_cart_service()
    cart = service.get_cart_with_totals(user_id=current_user.id)
    code = service.status_code
    return api_response(
        status_code=code,
        message="Cart is empty." if code == 201 else "Success",
        data=CartSchemas.Cart().dump(cart),
    )


@api_cart_bp.route("/items", methods=["POST"])
@jwt_required()
@api_cart_bp.arguments(CartSchemas.ItemCreate)
@api_cart_bp.response(201, CartSchemas.Response)
def add_to_cart(item_data):
    """Add an item to the user's cart."""
    service = get_cart_service()
    item, cart = service.add_item_to_cart(
        user_id=current_user.id,
        data=item_data
    )
    return api_response(
        status_code=201,
        message=f"{item.product.name} added to cart.",
        data=CartSchemas.Cart().dump(cart),
    )


@api_cart_bp.route("/items", methods=["DELETE"])
@jwt_required()
@api_cart_bp.response(200, CartSchemas.Response)
def clear_cart():
    """Remove all items from the user's cart."""
    service = get_cart_service()
    cart = service.clear_cart_items(user_id=current_user.id)
    return api_response(
        message="Cart cleared.",
        data=CartSchemas.Cart().dump(cart),
    )


@api_cart_bp.route("/items/<int:product_id>", methods=["PATCH"])
@jwt_required()
@api_cart_bp.arguments(CartSchemas.ItemUpdate)
@api_cart_bp.response(200, CartSchemas.Response)
def update_item_quantity(data, product_id):
    """Update quantity of a specific cart item."""
    service = get_cart_service()
    item, cart = service.update_cart_item_quantity(
        user_id=current_user.id,
        product_id=product_id,
        new_quantity=data["quantity"]
    )
    return api_response(
        message=f"{item.product.name} quantity updated to {data["quantity"]}."
                if data["quantity"] > 0
                else f"Item deleted.",
        data=CartSchemas.Cart().dump(cart),
    )


@api_cart_bp.route("/items/<int:product_id>", methods=["DELETE"])
@jwt_required()
@api_cart_bp.response(200, CartSchemas.Response)
def remove_cart_item(product_id):
    """Remove a specific item from the cart."""
    service = get_cart_service()
    cart = service.remove_item(
        user_id=current_user.id,
        product_id=product_id,
    )
    return api_response(
        message="Item removed from cart.",
        data=CartSchemas.Cart().dump(cart),
    )


@api_cart_bp.route("/checkout", methods=["POST"])
@api_cart_bp.doc(parameters=[{
    "name": "Idempotency-Key",
    "in": "header",
    "description": "Key to prevent duplicate requests.",
    "required": True,
}])
@jwt_required()
@idempotent_route
@limiter.limit("10 per minute")
@api_cart_bp.arguments(OrderSchemas.AddressCreate)
@api_cart_bp.response(201, CartSchemas.CheckoutResponse)
def checkout(checkout_data):
    """Checkout the user's cart and create a new order and payment."""
    service = get_cart_service()
    order, payment = service.checkout_cart(
        user_id=current_user.id,
        checkout_data=checkout_data,
    )
    return api_response(
        status_code=201,
        message="Successful checkout.",
        data={
            "order": OrderSchemas.Base().dump(order),
            "payment": PaymentSchemas.Base().dump(payment),
        }
    )