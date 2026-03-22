import hashlib
import hmac
import json
import uuid
import os
from dotenv import load_dotenv

PAYMENT_PAYLOAD = {
  "payment_id": 3,
  "event": "success"
}
DELIVERY_PAYLOAD = {
    "order_id": 3
}
FASTAPI_PAYLOAD = {
    "order_id": 102,
    "user_id": 999,
    "order_amount": 12.50,
    "orders_last_24h": 8,
    "is_shipping_billing_mismatch": True,
    "shipping_country": "GB",
    "ip_country": "US",
    "account_age_min": 5
}

load_dotenv()

def generate_signature_header(payload, testing=False):
    secret_key = os.getenv("TEST_WEBHOOK_SECRET_KEY") if testing else os.getenv("WEBHOOK_SECRET_KEY")
    normalized_payload = json.dumps(
        payload,
        separators=(",", ":"),
        sort_keys=True
    )
    signature = hmac.new(
        key=secret_key.encode(),
        msg=normalized_payload.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()

    return signature

if __name__ == '__main__':
    print(f"HMAC Signature for Payment: {generate_signature_header(PAYMENT_PAYLOAD)}")
    print(f"HMAC Signature for Delivery: {generate_signature_header(DELIVERY_PAYLOAD)}")
    print(f"HMAC Signature for Fraud Service: {generate_signature_header(FASTAPI_PAYLOAD)}")
    print(f"Idempotency Key: {uuid.uuid4()}")