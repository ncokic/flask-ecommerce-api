from decimal import Decimal
from unittest.mock import MagicMock

import pytest


class TestCartService:
    @pytest.mark.parametrize("item_in_cart, expected_quantity", [
        pytest.param(MagicMock(quantity=2), 5, id="item_exists_in_cart"),
        pytest.param(None, 3, id="item_not_found_in_cart")
    ])
    def test_add_quantity_to_cart_item(self, mock_cart_service, item_in_cart, expected_quantity):
        service, mocks = mock_cart_service
        data = {"product_id": 1, "quantity": 3}
        mocks["cart_item_repo"].find_product_in_cart.return_value = item_in_cart

        if not item_in_cart:
            mocks["cart_item_repo"].add_item_to_cart.return_value = MagicMock(quantity=3)

        cart_item, cart = service.add_item_to_cart(user_id=1, data=data)
        assert cart_item.quantity == expected_quantity
        mocks["session"].commit.assert_called_once()

    def test_calculate_cart_totals(self, mock_cart_service):
        service, mocks = mock_cart_service
        mock_item1 = MagicMock(quantity=2, product=MagicMock(price=Decimal("10.99")))
        mock_item2 = MagicMock(quantity=1, product=MagicMock(price=Decimal("29.99")))
        mock_cart = MagicMock(items=[mock_item1, mock_item2])

        total_items, total_cost = service.calculate_totals(mock_cart)
        assert total_items == 3
        assert total_cost == Decimal("51.97")

    def test_calculate_cart_totals_empty_cart(self, mock_cart_service):
        service, mocks = mock_cart_service
        mock_cart = MagicMock(items=[])
        total_items, total_cost = service.calculate_totals(mock_cart)
        assert total_items == 0
        assert total_cost == Decimal("0.00")

    @pytest.mark.parametrize("scenario, quantity", [
        pytest.param("update", 2, id="update_cart_item_quantity"),
        pytest.param("delete", 0, id="delete_cart_item")
    ])
    def test_update_item_quantity(self, mock_cart_service, scenario, quantity):
        service, mocks = mock_cart_service
        mock_item = MagicMock(product_id=1, quantity=5)
        mock_cart = MagicMock(id=1, items=[mock_item])

        mocks["cart_item_repo"].find_product_in_cart.return_value = mock_item
        mocks["cart_repo"].get_cart_by_user_id.return_value = mock_cart

        item, cart = service.update_cart_item_quantity(user_id=1, product_id=mock_item.product_id, new_quantity=quantity)
        if scenario == "update":
            assert item.quantity == 2
            mocks["cart_item_repo"].remove.assert_not_called()
        else:
            assert item is None
            mocks["cart_item_repo"].remove.assert_called_once()

        mocks["session"].commit.assert_called_once()