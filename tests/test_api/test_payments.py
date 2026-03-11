import uuid

import pytest

from scripts.generate_headers import generate_signature_header


class TestPayments:
    @pytest.mark.parametrize("event, payment_status, expected_code", [
        pytest.param("success", "pending", 200, id="pending_payment_accepted"),
        pytest.param("failure", "pending", 200, id="pending_payment_rejected"),
        pytest.param("success", "accepted", 409, id="invalid_payment_status"),
        pytest.param("custom", "pending", 422, id="invalid_payment_event"),
    ])
    def test_payment_webhook_event_and_status(
            self, client, test_user, seed_order, seed_payment, event, payment_status, expected_code
    ):
        payment = seed_payment
        payment.status = payment_status
        payload = {"payment_id": payment.id, "event": event}
        headers = {
            "Idempotency-Key": str(uuid.uuid4()),
            "X-Signature": generate_signature_header(payload)
        }
        response = client.post("/api/payments/webhook", json=payload, headers=headers)
        assert response.status_code == expected_code
        if response.status_code == 200:
            data = response.get_json()["data"]
            if event == "success":
                assert data["order_status"]["status"] == "paid"
                assert data["payment_status"]["status"] == "accepted"
            elif event == "failure":
                assert data["order_status"]["status"] == "pending"
                assert data["payment_status"]["status"] == "rejected"
            else:
                assert "invalid payment event" in response.get_json()["message"].lower()
