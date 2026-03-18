import pytest


class TestAdmin:
    def test_admin_decorator_protection(self, client, test_user):
        response = client.get("api/admin/products", headers=test_user["headers"])
        assert response.status_code == 403
        assert "admin access required" in response.get_json()["message"].lower()

    @pytest.mark.parametrize("query_args, expected_data", [
        pytest.param(
            "?page=2&per_page=5",
            {"count": 5, "total": 16}, # 15 + admin
            id="user_pagination",
        ),
        pytest.param(
            "?search_username=user_4",
            {"count": 1, "total": 1},
            id="user_filtering_by_username"
        ),
        pytest.param(
            "?search_username=user_9999",
            {"count": 0, "total": 0},
            id="user_filtering_no_results",
        ),
        pytest.param(
            "?sort=name_desc",
            {"count": 5, "first_user": "user_9"},
            id="user_sorting_by_name_descending"
        ),
    ])
    def test_user_pagination_filtering_sorting(self, client, admin_user, seed_users, query_args, expected_data):
        response = client.get(f"/api/admin/users{query_args}", headers=admin_user["headers"])
        assert response.status_code == 200
        users = response.get_json()["data"]["users"]
        assert len(users) == expected_data["count"]

        if "total" in expected_data:
            assert response.get_json()["data"]["total"] == expected_data["total"]
        if "first_user" in expected_data:
            assert users[0]["username"] == expected_data["first_user"]

    @pytest.mark.parametrize("user_id, expected_status", [
        pytest.param(5, 200, id="user_exists"),
        pytest.param(9999, 404, id="user_does_not_exist"),
    ])
    def test_get_user_by_id(self, client, admin_user, seed_users, user_id, expected_status):
        response = client.get(f"/api/admin/users/{user_id}", headers=admin_user["headers"])
        assert response.status_code == expected_status
        if response.status_code == 200:
            data = response.get_json()["data"]
            assert data["id"] == user_id

    @pytest.mark.parametrize("current_status, new_status, expected_code", [
        pytest.param("paid", "processing", 200, id="valid_transition_paid_to_processing"),
        pytest.param("processing", "shipped", 200, id="valid_transition_processing_to_shipped"),
        pytest.param("pending", "shipped", 409, id="invalid_transition_pending_to_shipped"),
    ])
    def test_change_order_status(
            self, client, admin_user, seed_order, current_status, new_status, expected_code
    ):
        order = seed_order
        order.status = current_status
        payload = {"status": new_status}
        response = client.patch(f"/api/admin/orders/{order.id}", json=payload, headers=admin_user["headers"])
        assert response.status_code == expected_code
        if response.status_code == 200:
            data = response.get_json()["data"]
            assert data["status"] == new_status
        else:
            assert "invalid" in response.get_json()["message"].lower()

    @pytest.mark.parametrize("refund_status, refund_accepted, order_returned, expected_code", [
        pytest.param("pending", True, True, 200, id="refund_accepted_order_returned"),
        pytest.param("pending", False, True, 200, id="refund_not_accepted"),
        pytest.param("accepted", True, True, 409, id="refund_already_processed"),
    ])
    def test_handle_refund(
            self, client, admin_user, seed_order, seed_refund_request,
            refund_status, refund_accepted, order_returned, expected_code,
    ):
        refund = seed_refund_request
        refund.status = refund_status
        payload = {"accepted": refund_accepted, "order_returned": order_returned}
        response = client.patch(
            f"/api/admin/orders/{seed_order.id}/refund",
            json=payload,
            headers=admin_user["headers"]
        )
        assert response.status_code == expected_code
        if response.status_code == 200:
            refund = response.get_json()["data"]["refund_request"]
            assert refund["status"] == "accepted" if refund_accepted else "rejected"
        else:
            assert "already processed" in response.get_json()["message"].lower()

    @pytest.mark.parametrize("order_id, expected_status", [
        pytest.param(1, 200, id="payment_exists"),
        pytest.param(9999, 404, id="payment_does_not_exist"),
    ])
    def test_get_payment(self, client, admin_user, seed_payment, order_id, expected_status):
        response = client.get(f"/api/admin/payments/{order_id}", headers=admin_user["headers"])
        assert response.status_code == expected_status
        if response.status_code == 200:
            data = response.get_json()["data"]
            assert data["order"]

    @pytest.mark.parametrize("action, order_status, expected_status", [
        pytest.param("approve", "pending_review", 200, id="flagged_order_accepted"),
        pytest.param("reject", "pending_review", 200, id="flagged_order_rejected"),
        pytest.param("invalid", "pending_review", 422, id="invalid_request"),
        pytest.param("approve", "pending", 400, id="invalid_order_status")
    ])
    def test_review_flagged_order(
            self, client, admin_user, seed_payment, action, order_status, expected_status
    ):
        order = seed_payment.order
        order.status = order_status
        response = client.patch(
            f"/api/admin/orders/{order.id}/review_flagged",
            json={"action": action},
            headers=admin_user["headers"]
        )
        assert response.status_code == expected_status
        if response.status_code == 200:
            data = response.get_json()["data"]
            assert data["status"] != "pending_review"