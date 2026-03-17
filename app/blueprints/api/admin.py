from flask_smorest import Blueprint

from app.schemas.orders import OrderSchemas
from app.schemas.payments import PaymentSchemas
from app.schemas.products import ProductSchemas
from app.schemas.users import UserSchemas
from app.services.helpers import get_user_service, get_product_service, get_order_service, get_payment_service, \
    split_query_args
from app.utils.responses import api_response
from app.utils.security import admin_only

api_admin_bp = Blueprint(
    "api_admin",
    __name__,
    url_prefix="/api/admin",
    description="Admin operations",
)


@api_admin_bp.route("/products")
@admin_only
@api_admin_bp.arguments(ProductSchemas.Query, location="query")
@api_admin_bp.response(200, ProductSchemas.ListAdminResponse)
def get_inventory(args):
    """Retrieve a list of products, supports optional pagination, filtering and sorting."""
    service = get_product_service()
    page, per_page, filters, sort = split_query_args(args)
    products, total = service.get_products(
        page=page,
        per_page=per_page,
        filters=filters,
        sort=sort,
    )
    return api_response(data={
        "products": ProductSchemas.Admin(many=True).dump(products),
        "total": total,
        "page": page,
        "per_page": per_page,
    })


@api_admin_bp.route("/users")
@admin_only
@api_admin_bp.arguments(UserSchemas.Query, location="query")
@api_admin_bp.response(200, UserSchemas.ListAdminResponse)
def get_users(args):
    """Retrieve a list of registered users, supports optional pagination, filtering and sorting."""
    service = get_user_service()
    page, per_page, filters, sort = split_query_args(args)
    users, total = service.get_users(
        page=page,
        per_page=per_page,
        filters=filters,
        sort=sort,
    )
    return api_response(data={
        "users": UserSchemas.Admin(many=True).dump(users),
        "total": total,
        "page": page,
        "per_page": per_page,
    })


@api_admin_bp.route("/orders")
@admin_only
@api_admin_bp.arguments(OrderSchemas.AdminQuery, location="query")
def get_orders(args):
    """Retrieve a list of orders, supports optional pagination, filtering and sorting."""
    service = get_order_service()
    page, per_page, filters, sort = split_query_args(args)
    orders, total = service.list_orders(
        page=page,
        per_page=per_page,
        filters=filters,
        sort=sort,
    )
    return api_response(data={
        "order": OrderSchemas.Base(many=True).dump(orders),
        "total": total,
        "page": page,
        "per_page": per_page,
    })


@api_admin_bp.route("/products/<int:product_id>")
@admin_only
@api_admin_bp.response(200, ProductSchemas.AdminResponse)
def get_product(product_id):
    """Retrieve detailed information for a specific product."""
    service = get_product_service()
    product = service.get_product_by_id(product_id)
    return api_response(data=ProductSchemas.Admin().dump(product))


@api_admin_bp.route("/users/<int:user_id>")
@admin_only
@api_admin_bp.response(200, UserSchemas.AdminResponse)
def get_user(user_id):
    """Retrieve detailed information for a specific user."""
    service = get_user_service()
    user = service.get_user_by_id(user_id)
    return api_response(data=UserSchemas.Admin().dump(user))


@api_admin_bp.route("/orders/<int:order_id>", methods=["PATCH"])
@admin_only
@api_admin_bp.arguments(OrderSchemas.Status)
@api_admin_bp.response(200, OrderSchemas.Response)
def change_order_status(data, order_id):
    """Update the status of a specific order."""
    service = get_order_service()
    order = service.change_order_status(order_id, data.status)
    return api_response(data=OrderSchemas.Base().dump(order))


@api_admin_bp.route("/orders/<int:order_id>/review_flagged", methods=["PATCH"])
@admin_only
@api_admin_bp.arguments(OrderSchemas.ReviewFraud)
@api_admin_bp.response(200, OrderSchemas.Response)
def review_flagged_order(data, order_id):
    """Process potentially fraudulent orders flagged by FastAPI Fraud Check Microservice."""
    service = get_order_service()
    order = service.review_flagged_order(order_id, data["action"])
    return api_response(
        message=f"Order reviewed - status changed to {order.status}",
        data=OrderSchemas.Base().dump(order)
    )


@api_admin_bp.route("/orders/<int:order_id>/refund", methods=["PATCH"])
@admin_only
@api_admin_bp.arguments(PaymentSchemas.RefundReview)
@api_admin_bp.response(200, OrderSchemas.Response)
def handle_refund(data, order_id):
    """Process a refund for a specific order after an admin review."""
    service = get_payment_service()
    order = service.handle_refund_request(
        order_id=order_id,
        refund_accepted=data["accepted"],
        order_returned=data["order_returned"],
    )
    return api_response(
        message="Refund request handled.",
        data=OrderSchemas.Base().dump(order),
    )


@api_admin_bp.route("/payments/<int:order_id>")
@admin_only
@api_admin_bp.response(200, PaymentSchemas.Response)
def get_order_payment(order_id):
    """Retrieve payment details for a specific order."""
    service = get_payment_service()
    payment = service.get_payment(order_id)
    return api_response(data=PaymentSchemas.Base().dump(payment))
