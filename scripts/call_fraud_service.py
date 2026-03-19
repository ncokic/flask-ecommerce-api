import hashlib
import hmac
import json
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

PAYLOAD = {
    "order_id": 20,
    "user_id": 40,
    "order_amount": 15.99,
    "orders_last_24h": 2,
    "is_shipping_billing_mismatch": True,
    "shipping_country": "US",
    "ip_country": "GB",
    "account_age_min": 20
}
SECRET_KEY = os.getenv("WEBHOOK_SECRET_KEY")
FRAUD_SERVICE_URL = os.getenv("FRAUD_SERVICE_URL")


def call_fraud_model(payload):
    normalized_payload = json.dumps(
        payload,
        separators=(",", ":"),
        sort_keys=True
    )
    signature = hmac.new(
        key=SECRET_KEY.encode(),
        msg=normalized_payload.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()

    response = httpx.post(
        url=f"{FRAUD_SERVICE_URL}/check_fraud",
        json=payload,
        headers={"X-Signature": signature}
    )

    response.raise_for_status()
    data = response.json()
    print (json.dumps(data, indent=4))


if __name__ == "__main__":
    call_fraud_model(payload=PAYLOAD)