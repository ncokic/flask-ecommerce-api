from flask_jwt_extended import jwt_required, current_user
from flask_smorest import Blueprint

from app.extensions import limiter
from app.schemas.orders import OrderSchemas
from app.schemas.payments import PaymentSchemas
from app.services.helpers import get_order_service, get_payment_service
from app.utils.responses import api_response
from app.utils.security import idempotent_route, signature_required

api_orders_bp = Blueprint(
    "api_orders",
    __name__,
    url_prefix="/api/orders",
    description="Order management endpoints",
)


@api_orders_bp.route("")
@jwt_required()
@api_orders_bp.arguments(OrderSchemas.Query, location="query")
@api_orders_bp.response(200, OrderSchemas.ListResponse)
def list_orders(args):
    """Retrieve a list of user's orders, supports optional pagination, filtering and sorting."""
    service = get_order_service()
    page = args.pop("page", None)
    per_page = args.pop("per_page", None)
    sort = args.pop("sort", None)
    orders, total = service.list_user_orders(
        current_user.id,
        page=page,
        per_page=per_page,
        filters=args,
        sort=sort,
    )
    return api_response(data={
        "orders": OrderSchemas.Base(many=True).dump(orders),
        "total": total,
        "page": page,
        "per_page": per_page,
    })


@api_orders_bp.route("/<int:order_id>")
@jwt_required()
@api_orders_bp.response(200, OrderSchemas.Response)
def get_order(order_id):
    """Retrieve detailed information for user's specific order."""
    service = get_order_service()
    order = service.get_user_order(
        user_id=current_user.id,
        order_id=order_id,
    )
    return api_response(data=OrderSchemas.Base().dump(order))


@api_orders_bp.route("/<int:order_id>/cancel", methods=["PATCH"])
@api_orders_bp.doc(parameters=[{
    "name": "Idempotency-Key",
    "in": "header",
    "description": "Key to prevent duplicate requests.",
    "required": True,
}])
@jwt_required()
@idempotent_route
@limiter.limit("5 per minute")
@api_orders_bp.response(200, OrderSchemas.Response)
def cancel_order(order_id):
    """Cancel a pending or paid order within the cancellation window."""
    service = get_order_service()
    order = service.cancel_order(
        user_id=current_user.id,
        order_id=order_id,
    )
    return api_response(
        message="Order cancelled.",
        data=OrderSchemas.Base().dump(order),
    )


@api_orders_bp.route("/<int:order_id>/refund", methods=["POST"])
@api_orders_bp.doc(parameters=[{
    "name": "Idempotency-Key",
    "in": "header",
    "description": "Key to prevent duplicate requests.",
    "required": True,
}])
@jwt_required()
@idempotent_route
@api_orders_bp.arguments(PaymentSchemas.RefundRequest)
@api_orders_bp.response(201, OrderSchemas.Response)
def request_refund(data, order_id):
    """Request refund for a delivered order within the allowed timeframe."""
    service = get_payment_service()
    order = service.send_refund_request(
        user_id=current_user.id,
        order_id=order_id,
        reason=data["reason"],
    )
    return api_response(
        message="Refund request successful.",
        data=OrderSchemas.Base().dump(order)
    )


@api_orders_bp.route("/delivery_webhook", methods=["POST"])
@api_orders_bp.doc(
    security=[],
    parameters=[
        {
            "name": "X-Signature",
            "in": "header",
            "description": "Signature to access delivery provider.",
            "required": True,
        },
        {
            "name": "Idempotency-Key",
            "in": "header",
            "description": "Key to prevent duplicate requests.",
            "required": True,
        }
    ]
)
@signature_required
@idempotent_route
@api_orders_bp.arguments(OrderSchemas.WebhookCreate)
@api_orders_bp.response(200, OrderSchemas.WebhookResponse)
def delivery_webhook(data):
    """Simulate order delivery confirmation from the courier via webhook."""
    service = get_order_service()
    order = service.delivery_webhook(data["order_id"])
    return api_response(
        message="Delivery webhook processed.",
        data=OrderSchemas.Base().dump(order)
    )

