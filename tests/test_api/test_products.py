import pytest
from sqlalchemy import select

from app.extensions import db
from app.models import Product


class TestProducts:
    @pytest.mark.parametrize("product_id, expected_status", [
        pytest.param(5, 200, id="valid_request_payload"),
        pytest.param(9999, 404, id="product_does_not_exist"),
    ])
    def test_get_product(self, client, seed_products, product_id, expected_status):
        response = client.get(f"/api/products/{product_id}")
        assert response.status_code == expected_status

    @pytest.mark.parametrize("query_args, expected_data", [
        pytest.param(
            "?page=1&per_page=5",
            {"count": 5, "total": 15},
            id="pagination",
        ),
        pytest.param(
            "?category=Displays",
            {"count": 3},
            id="category_filter",
        ),
        pytest.param(
            "?sort=price_desc",
            # count=5 because default I set in schema for per_page is 5
            {"count": 5, "first_name": "32-inch Curved Monitor"},
            id="sorting",
        ),
        pytest.param(
            "?search=ProductThatDoesNotExist",
            {"count": 0},
            id="search_filter_empty"
        ),
    ])
    def test_list_products(self, client, seed_products, query_args, expected_data):
        response = client.get(f"/api/products{query_args}")
        assert response.status_code == 200

        data = response.get_json()["data"]
        assert len(data["products"]) == expected_data["count"]

        if "total" in expected_data:
            assert data["total"] == expected_data["total"]
        if "first_name" in expected_data:
            assert data["products"][0]["name"] == expected_data["first_name"]

    @pytest.mark.parametrize("key, value, expected_status", [
        pytest.param("name", "Test Product", 201, id="valid_request_payload"),
        pytest.param("name", "", 422, id="empty_request_field"),
        pytest.param("name", "x"*500, 422, id="name_too_long"),
        pytest.param("price", -1, 422, id="negative_price"),
        pytest.param("stock", -1, 422, id="negative_stock"),
    ])
    def test_create_product_as_admin(self, client, admin_user, expected_status, key, value):
        initial_count = len(db.session.execute(select(Product)).scalars().all())
        payload = {
            "name": "Test Product",
            "description": "Description for a test product",
            "category": "Test",
            "price": 129.99,
            "stock": 10,
            key: value,
        }
        response = client.post("/api/products", json=payload, headers=admin_user["headers"])
        assert response.status_code == expected_status

        current_count = len(db.session.execute(select(Product)).scalars().all())
        if response.status_code == 201:
            assert current_count == initial_count + 1
        else:
            assert current_count == initial_count

    def test_update_product_as_admin(self, client, seed_products, admin_user):
        product = seed_products[0]
        payload = {"name": "Updated Name", "price": 29.99}
        response = client.patch(f"/api/products/{product.id}", json=payload, headers=admin_user["headers"])
        assert response.status_code == 200

        data = response.get_json()["data"]
        assert data["name"] == payload["name"]
        assert data["price"] == str(payload["price"])
        assert data["description"] == product.description

    def test_delete_product_as_admin(self, client, seed_products, admin_user):
        product = seed_products[0]
        response = client.delete(f"/api/products/{product.id}", headers=admin_user["headers"])
        assert response.status_code == 200

        deleted_product = db.session.get(Product, product.id)
        assert deleted_product is None

        response = client.delete(f"/api/products/{product.id}", headers=admin_user["headers"])
        assert response.status_code == 404