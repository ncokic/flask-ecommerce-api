from datetime import datetime, timedelta, UTC, timezone

import country_converter as coco
import httpx
import ipapi
from flask import request

from app.repositories import OrderRepository
from scripts.generate_headers import generate_signature_header
from config import Config


class FraudService:
    def __init__(self, order_repo: OrderRepository):
        self.order_repo = order_repo

    def gather_data(self, order, checkout_data, client_ip=None):
        one_day_ago = datetime.now() - timedelta(hours=24)
        orders_last_24h = self.order_repo.count_user_orders_last_24h(order.user_id, one_day_ago)

        billing_same_as_shipping = checkout_data["billing_same_as_shipping"]
        shipping_address = checkout_data["shipping_address"]
        shipping_country = coco.convert(
            names=shipping_address["country"], to="iso2")

        if not client_ip:
            client_ip = request.remote_addr
        # manual ip for testing purposes
        if client_ip in ["localhost", "127.0.0.1"] or client_ip.startswith("172."):
            client_ip = "8.8.8.8"
        location_data = ipapi.location(client_ip)
        country_code = location_data.get("country") if location_data else None
        ip_country = country_code if (country_code and len(country_code) == 2) else "US"

        user_created = order.user.created_at
        if user_created.tzinfo is None:
            user_created = user_created.replace(tzinfo=timezone.utc)

        acc_age = datetime.now(UTC) - user_created
        acc_age_min = int(acc_age.total_seconds() / 60)

        return {
            "order_id": order.id,
            "user_id": order.user_id,
            "order_amount": float(order.total_amount),
            "orders_last_24h": orders_last_24h,
            "is_shipping_billing_mismatch": False if billing_same_as_shipping else True,
            "shipping_country": shipping_country,
            "ip_country": ip_country,
            "account_age_min": acc_age_min
        }

    def check_fraud(self, order, checkout_data):
        payload = self.gather_data(order, checkout_data)
        with httpx.Client(base_url=Config.FRAUD_SERVICE_URL) as client:
            try:
                timeout = httpx.Timeout(5.0, connect=2.0)
                headers = {
                    "X-Signature": generate_signature_header(payload)
                }
                response = client.post("/check_fraud", json=payload, headers=headers, timeout=timeout)
                return response.json()

            except httpx.ConnectTimeout:
                return self.fraud_service_down(order.id, "CONNECTION_TIMEOUT")

            except httpx.ReadTimeout:
                return self.fraud_service_down(order.id, "PROCESSING_TIMEOUT")

            except httpx.HTTPStatusError:
                return self.fraud_service_down(order.id, "SERVER_ERROR")

            except httpx.RequestError:
                return self.fraud_service_down(order.id, "NETWORK_ERROR")

    @staticmethod
    def fraud_service_down(order_id, reason):
        return {
            "order_id": order_id,
            "risk_assessment": "low",
            "risk_score": f"Fraud check skipped: {reason}"
        }