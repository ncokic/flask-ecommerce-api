from datetime import datetime, UTC, timedelta
import uuid

import pytest

from scripts.generate_headers import generate_signature_header


class TestOrders:
    @pytest.mark.parametrize("order_id, expected_response", [
        pytest.param(1, 200, id="valid_request_payload"),
        pytest.param(9999, 404, id="order_does_not_exist"),
    ])
    def test_get_order(self, client, test_user, seed_order, order_id, expected_response):
        response = client.get(f"/api/orders/{order_id}", headers=test_user["headers"])
        assert response.status_code == expected_response
        if response.status_code == 200:
            data = response.get_json()["data"]
            assert data["items"] is not None
            assert data["status"] == "pending"

    def test_order_forbidden_for_wrong_user(self, client, admin_user, seed_order):
        response = client.get(f"/api/orders/{seed_order.id}", headers=admin_user["headers"])
        assert response.status_code == 404
        assert "not found" in response.get_json()["message"].lower()

    @pytest.mark.parametrize("query_args, expected_data", [
        pytest.param(
            "?page=1&per_page=5",
            {"count": 5, "total": 12},
            id="pagination",
        ),
        pytest.param(
            "?status=shipped",
            {"count": 2},
            id="status_filter",
        ),
        pytest.param(
            "?sort=oldest",
            {"count": 5}, #default pagination per_page is 5
            id="sorting",
        ),
    ])
    def test_list_orders(self, client, test_user, seed_orders, query_args, expected_data):
        response = client.get(f"/api/orders{query_args}", headers=test_user["headers"])
        assert response.status_code == 200
        orders = response.get_json()["data"]["orders"]
        assert len(orders) == expected_data["count"]

        if "total" in expected_data:
            assert response.get_json()["data"]["total"] == expected_data["total"]
        if "status" in query_args:
            assert orders[0]["status"] == "shipped"
        if "sort=oldest" in query_args:
            assert all(x["created_at"] <= y["created_at"] for x, y in zip(orders, orders[1:]))

    @pytest.mark.parametrize("order_status, expected_code", [
        pytest.param("pending", 200, id="pending_order"),
        pytest.param("paid", 200, id="paid_order"),
        pytest.param("shipped", 409, id="shipped_order"),
    ])
    def test_cancel_order(self, client, test_user, seed_order, order_status, expected_code):
        order = seed_order
        order.status = order_status
        order.created_at = datetime.now(UTC) - timedelta(minutes=15)
        headers = {
            "Authorization": f"Bearer {test_user["access_token"]}",
            "Idempotency-Key": str(uuid.uuid4())
        }
        response = client.patch(f"/api/orders/{order.id}/cancel", headers=headers)
        assert response.status_code == expected_code
        if response.status_code == 200:
            data = response.get_json()["data"]
            assert data["status"] == "cancelled"
            if order_status == "paid":
                assert data["refund_request"]["status"] == "accepted"

    @pytest.mark.parametrize("order_status, delivered_at, reason, expected_code",  [
        pytest.param(
            "delivered",
            datetime.now(UTC) - timedelta(days=6),
            "not_as_described",
            200,
            id="valid_request_payload_active_refund_window",
        ),
        pytest.param(
            "delivered",
            datetime.now(UTC) - timedelta(days=8),
            "damaged_item",
            409,
            id="valid_request_payload_active_refund_window",
        ),
        pytest.param(
            "paid",
            None,
            "wrong_item",
            409,
            id="invalid_order_status_first",
        ),
        pytest.param(
            "shipped",
            None,
            "wrong_item",
            409,
            id="invalid_order_status_second",
        ),
        pytest.param(
            "delivered",
            datetime.now(UTC) - timedelta(days=6),
            "custom_reason",
            422,
            id="invalid_payload_data",
        ),
    ])
    def test_refund_request_order_status_and_refund_window(
            self, client, test_user, seed_order, order_status, delivered_at, reason, expected_code
    ):
        order = seed_order
        order.status = order_status
        order.delivered_at = delivered_at
        payload = {"reason": f"{reason}"}
        headers = {
            "Authorization": f"Bearer {test_user["access_token"]}",
            "Idempotency-Key": str(uuid.uuid4())
        }
        response = client.post(f"/api/orders/{seed_order.id}/refund", json=payload, headers=headers)
        assert response.status_code == expected_code
        if response.status_code == 200:
            data = response.get_json()["data"]
            assert data["refund_request"]["status"] == "pending"
            assert data["refund_request"]["reason"] == reason

    @pytest.mark.parametrize("order_status, sig_provided, sig_valid, expected_code", [
        pytest.param("shipped", True, True, 200, id="order_shipped_signature_valid"),
        pytest.param("processing", True, True, 409, id="order_not_yet_shipped_signature_valid"),
        pytest.param("shipped", True, False, 401, id="signature_invalid"),
        pytest.param("shipped", False, False, 401, id="signature_not_provided"),
    ])
    def test_delivery_webhook_order_status_and_signature_validation(
            self, client, test_user, seed_order, order_status, sig_provided, sig_valid, expected_code
    ):
        order = seed_order
        order.status = order_status
        payload = {"order_id": f"{order.id}"}
        signature = generate_signature_header(payload)
        signature = signature if sig_valid else signature + "a"
        headers = {
            "Idempotency-Key": str(uuid.uuid4()),
            "X-Signature": signature if sig_provided else ""
        }
        response = client.post("api/orders/delivery_webhook", json=payload, headers=headers)
        assert response.status_code == expected_code
        if response.status_code == 200:
            data = response.get_json()["data"]
            assert data["status"] == "delivered"

        elif response.status_code == 401:
            message = response.get_json()["message"].lower()
            if sig_provided:
                assert "invalid signature" in message
            else:
                assert "header required" in message
