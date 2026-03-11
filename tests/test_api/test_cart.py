import json
import uuid

import pytest
from sqlalchemy import delete

from app.extensions import db, redis_client
from app.models import CartItem

ADDRESS_PAYLOAD = {
    "full_name": "Test Name",
    "street": "Test Street 123",
    "city": "TestCity",
    "postal_code": "12345",
    "country": "TestCountry",
    "contact_phone": "+12345678"
}


class TestCart:
    def test_get_cart(self, client, test_user):
        response_create = client.get("api/cart", headers=test_user["headers"])
        assert response_create.status_code == 201
        data_create = response_create.get_json()["data"]

        response_get = client.get("api/cart", headers=test_user["headers"])
        assert response_get.status_code == 200
        data_get = response_get.get_json()["data"]
        assert data_get["cart"]["id"] == data_create["cart"]["id"]

    @pytest.mark.parametrize("prod_id, quantity, expected_response", [
        pytest.param(1, 1, 201, id="valid_request_payload"),
        pytest.param(999, 1, 404, id="product_does_not_exist"),
        pytest.param(1, -1, 422, id="negative_quantity"),
        pytest.param(5, "", 422, id="empty_request_field"),
        pytest.param(1, "abc", 422, id="invalid_request_format"),
    ])
    def test_add_item_to_cart_validation(self, client, test_user, seed_products, prod_id, quantity, expected_response):
        payload = {"product_id": prod_id, "quantity": quantity}
        response = client.post("/api/cart/items", json=payload, headers=test_user["headers"])
        assert response.status_code == expected_response
        if response.status_code == 201:
            item = response.get_json()["data"]["cart"]["items"][0]
            assert item["product"]["id"] == prod_id
            assert item["quantity"] == quantity

    @pytest.mark.parametrize("prod_id, quantity", [
        pytest.param(1, 2, id="update_product_quantity"),
        pytest.param(1, 0, id="remove_item_from_cart"),
    ])
    def test_update_or_remove_cart_item(self, client, test_user, seed_cart, seed_products, prod_id, quantity):
        cart, items = seed_cart
        item_id = items[0].id

        payload = {"quantity": quantity}
        response = client.patch(f"/api/cart/items/{prod_id}", json=payload, headers=test_user["headers"])
        assert response.status_code == 200
        if quantity > 0:
            item = response.get_json()["data"]["cart"]["items"][0]
            assert item["quantity"] == quantity
        else:
            deleted_item = db.session.get(CartItem, item_id)
            assert deleted_item is None

    def test_clear_cart(self, client, test_user, seed_cart):
        cart, items = seed_cart
        assert cart.items
        response = client.delete("/api/cart/items", headers=test_user["headers"])
        assert response.status_code == 200
        data = response.get_json()["data"]
        assert not data["cart"]["items"]

    @pytest.mark.parametrize("key, value, cart_has_items, expected_status", [
        pytest.param("full_name", "Test Name", True, 201, id="valid_request_payload_cart_has_items"),
        pytest.param("full_name", "Test Name", False, 422, id="valid_request_payload_cart_is_empty"),
        pytest.param("street", "", True, 422, id="empty_request_field"),
        pytest.param("postal_code", 12345, True, 422, id="invalid_postal_code_format"),
        pytest.param("contact_phone", "12345", True, 422, id="invalid_contact_phone_format"),
    ])
    def test_checkout_address_validation(
            self, client, test_user, seed_cart, seed_products, key, value, cart_has_items, expected_status
    ):
        cart, items = seed_cart
        if cart_has_items:
            item_product_id = items[0].product.id
        else:
            item_product_id = None
            db.session.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
            db.session.commit()
        headers = {
            "Authorization": f"Bearer {test_user["access_token"]}",
            "Idempotency-Key": str(uuid.uuid4())
        }
        payload = ADDRESS_PAYLOAD | {key: value}

        response = client.post("api/cart/checkout", json=payload, headers=headers)
        assert response.status_code == expected_status
        if response.status_code == 201:
            data = response.get_json()["data"]
            product_in_cart = data["order"]["items"][0]["product"]
            assert product_in_cart["id"] == item_product_id
            assert data["payment"]["status"] == "pending"

    @pytest.mark.parametrize("scenario, first_status, second_status", [
        pytest.param("duplicate", 201, 200, id="duplicate_request"),
        pytest.param("mismatch", 201, 400, id="key_and_body_mismatch"),
    ])
    def test_checkout_idempotency(
            self, client, test_user, seed_cart, seed_products, scenario, first_status, second_status
    ):
        idempotency_key = str(uuid.uuid4())
        headers = {
            "Authorization": f"Bearer {test_user["access_token"]}",
            "Idempotency-Key": idempotency_key
        }
        payload = ADDRESS_PAYLOAD

        response = client.post("/api/cart/checkout", json=payload, headers=headers)
        assert response.status_code == first_status

        if scenario == "mismatch":
            payload["name"] = "Changed Name"

        response = client.post("/api/cart/checkout", json=payload, headers=headers)
        assert response.status_code == second_status
        message = response.get_json()["message"].lower()
        if response.status_code == 200:
            assert "already processed" in message
        else:
            assert "mismatch" in message

    def test_checkout_request_already_in_progress(self, app, client, test_user, seed_cart, seed_products):
        idempotency_key = str(uuid.uuid4())
        cached_data = {"status": "in_progress"}
        app.redis_client.set(idempotency_key, json.dumps(cached_data))

        headers = {
            "Authorization": f"Bearer {test_user["access_token"]}",
            "Idempotency-Key": idempotency_key
        }
        payload = ADDRESS_PAYLOAD

        response = client.post("/api/cart/checkout", json=payload,  headers=headers)
        assert response.status_code == 409
        assert "in progress" in response.get_json()["message"].lower()
