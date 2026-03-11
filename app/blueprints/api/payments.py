from flask_smorest import Blueprint

from app.schemas.payments import PaymentSchemas
from app.services.helpers import get_payment_service
from app.utils.responses import api_response
from app.utils.security import signature_required, idempotent_route

api_payments_bp = Blueprint(
    "api_payments",
    __name__,
    url_prefix="/api/payments",
    description="Payment management endpoints",
)


@api_payments_bp.route("/webhook", methods=["POST"])
@api_payments_bp.doc(
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
@api_payments_bp.arguments(PaymentSchemas.WebhookCreate)
@api_payments_bp.response(200, PaymentSchemas.WebhookResponse)
def payment_webhook(data):
    """Simulate payment status update from the mock payment provider via webhook."""
    service = get_payment_service()
    payment = service.payment_webhook(
        payment_id=data["payment_id"],
        event=data["event"],
    )
    payload = {
        "order_status": payment.order,
        "payment_status": payment,
    }
    return api_response(
        message="Payment webhook processed.",
        data=PaymentSchemas.WebhookStatus().dump(payload),
    )
