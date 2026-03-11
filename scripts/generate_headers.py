import hashlib
import hmac
import json
import uuid

from flask import current_app

from app import create_app

PAYMENT_PAYLOAD = {
  "payment_id": 3,
  "event": "success"
}
DELIVERY_PAYLOAD = {
    "order_id": 3
}


def generate_signature_header(payload):
    secret_key = current_app.config.get("WEBHOOK_SECRET_KEY")
    normalized_payload = json.dumps(
        payload,
        separators=(",", ":"),
        sort_keys=True,
    )
    signature = hmac.new(
        key=secret_key.encode(),
        msg=normalized_payload.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()

    return signature

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        print(f"HMAC Signature for Payment: {generate_signature_header(PAYMENT_PAYLOAD)}")
        print(f"HMAC Signature for Delivery: {generate_signature_header(DELIVERY_PAYLOAD)}")
        print(f"Idempotency Key: {uuid.uuid4()}")