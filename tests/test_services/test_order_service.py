from datetime import datetime, UTC, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.utils.error_handlers import ServiceError


class TestOrderService:
    def test_create_order_insufficient_stock(self, mock_order_service):
        service, mocks = mock_order_service
        mock_product = MagicMock(name="Product", stock=2)
        mock_item = MagicMock(product=mock_product, quantity=3)
        mock_cart = MagicMock(items=[mock_item])
        checkout_payload = {
            "shipping_address": {"full_name": "Test User", "street": "Test Street 123"},
            "billing_same_as_shipping": True,
            "billing_address": None
        }

        with pytest.raises(ServiceError) as e:
            service.create_order(mock_cart, checkout_payload)

        assert e.value.status_code == 409
        assert "not in stock" in e.value.message.lower()
        mocks["session"].commit.assert_not_called()

    @pytest.mark.parametrize("existing_adr", [
        pytest.param(False, id="existing_shipping_address"),
        pytest.param(True, id="new_addresses")
    ])
    def test_create_order_address_checking(self, mock_order_service, existing_adr):
        service, mocks = mock_order_service
        mock_product = MagicMock(name="Product", price=Decimal("20.00"), stock=10)
        mock_item = MagicMock(product=mock_product, quantity=3)
        mock_cart = MagicMock(user_id=1, items=[mock_item])
        checkout_payload = {
            "shipping_address": {"full_name": "Test User", "street": "Test Street 123"},
            "billing_same_as_shipping": True,
            "billing_address": None
        }
        if existing_adr:
            ship_adr = MagicMock(id=10)
            mocks["ship_address_repo"].get_existing_address.return_value = ship_adr
        else:
            mocks["ship_address_repo"].get_existing_address.return_value = None
            ship_adr = MagicMock(id=100)
            mocks["ship_address_repo"].save.return_value =  ship_adr

        mocks["bill_address_repo"].get_existing_address.return_value = None
        bill_addr = MagicMock(id=20)
        mocks["bill_address_repo"].save.return_value = bill_addr

        mocks["fraud_service"].check_fraud.return_value = {
            "risk_assessment": "low",
            "risk_score": 10
        }

        order = service.create_order(mock_cart, checkout_payload)
        if existing_adr:
            mocks["ship_address_repo"].save.assert_not_called()
        else:
            mocks["ship_address_repo"].save.assert_called_once()
        mocks["bill_address_repo"].save.assert_called_once()
        assert order.total_amount == Decimal("60.00")
        assert order.shipping_address_id == 10 if existing_adr else 100
        assert order.billing_address_id == 20

    def test_cancel_order_invalid_status(self, mock_order_service):
        service, mocks = mock_order_service
        mock_order = MagicMock(id=1, status="shipped", created_at=datetime.now(UTC))
        mocks["order_repo"].get_user_order.return_value = mock_order

        with pytest.raises(ServiceError) as e:
            service.cancel_order(user_id=1, order_id=mock_order.id)

        assert e.value.status_code == 409
        assert "failed" in e.value.message.lower()
        mocks["session"].commit.assert_not_called()

    @pytest.mark.parametrize("minutes, should_fail", [
        pytest.param(61, True, id="cancellation_window_expired"),
        pytest.param(59, False, id="cancellation_window_active")
    ])
    def test_cancel_order_cancellation_window(self, mock_order_service, minutes, should_fail):
        service, mocks = mock_order_service
        mock_order = MagicMock(id=1, created_at=datetime.now(UTC)-timedelta(minutes=minutes))
        mocks["order_repo"].get_user_order.return_value = mock_order

        if should_fail:
            with pytest.raises(ServiceError) as e:
                service.cancel_order(user_id=1, order_id=mock_order.id)
            assert e.value.status_code == 409
            assert "window expired" in e.value.message.lower()
            mocks["session"].commit.assert_not_called()

        else:
            order = service.cancel_order(user_id=1, order_id=mock_order.id)
            assert order
            mocks["session"].commit.assert_called_once()

    def test_cancel_order_if_order_pending(self, mock_order_service):
        service, mocks = mock_order_service
        mock_order = MagicMock(id=1, status="pending", created_at=datetime.now(UTC))
        mocks["order_repo"].get_user_order.return_value = mock_order
        service.cancel_order(user_id=1, order_id=mock_order.id)
        assert mock_order.status == "cancelled"
        mocks["session"].commit.assert_called_once()

    def test_cancel_order_if_order_paid_refund_and_restock(self, mock_order_service):
        service, mocks = mock_order_service
        mock_product = MagicMock(stock=8)
        mock_item = MagicMock(product=mock_product, quantity=2)
        mock_order = MagicMock(
            id=1,
            status="paid",
            items=[mock_item],
            created_at=datetime.now(UTC),
        )
        mocks["order_repo"].get_user_order.return_value = mock_order

        service.cancel_order(user_id=1, order_id=mock_order.id)
        mocks["payment_service"].create_refund_request.assert_called_once()
        assert mock_product.stock == 10
        assert mock_order.status == "cancelled"
        mocks["session"].commit.assert_called_once()

    def test_delivery_webhook_if_not_shipped(self, mock_order_service):
        service, mocks = mock_order_service
        mock_order = MagicMock(id=1, status="paid")
        mocks["order_repo"].get_by_id.return_value = mock_order

        with pytest.raises(ServiceError) as e:
            service.delivery_webhook(order_id=mock_order.id)

        assert e.value.status_code == 409
        assert "only orders in shipping" in e.value.message.lower()
        mocks["session"].commit.assert_not_called()

    def test_delivery_webhook_if_shipped(self, mock_order_service):
        service, mocks = mock_order_service
        mock_order = MagicMock(id=1, status="shipped")
        mocks["order_repo"].get_by_id.return_value = mock_order
        order = service.delivery_webhook(order_id=mock_order.id)
        assert order.status == "delivered"
        mocks["session"].commit.assert_called_once()

    def test_change_order_status_invalid_transition(self, mock_order_service):
        service, mocks = mock_order_service
        mock_order = MagicMock(id=1, status="paid")
        mocks["order_repo"].get_by_id.return_value = mock_order

        with pytest.raises(ServiceError) as e:
            service.change_order_status(order_id=mock_order.id, new_status="shipped")

        assert e.value.status_code == 409
        assert "invalid" in e.value.message.lower()
        mocks["session"].commit.assert_not_called()

    @pytest.mark.parametrize("initial, target, expected", [
        pytest.param("paid", "processing", "processing", id="from_paid_to_processing"),
        pytest.param("processing", "shipped", "shipped", id="from_processing_to_shipped"),
    ])
    def test_change_order_status_valid_transition(self, mock_order_service, initial, target, expected):
        service, mocks = mock_order_service
        mock_order = MagicMock(id=1, status=initial)
        mocks["order_repo"].get_by_id.return_value = mock_order
        order = service.change_order_status(order_id=mock_order.id, new_status=target)
        assert order.status == expected
        mocks["session"].commit.assert_called_once()

    @pytest.mark.parametrize("action, expected_order_status", [
        pytest.param("approve", "pending", id="flagged_order_approved"),
        pytest.param("reject", "rejected", id="flagged_order_rejected")
    ])
    def test_review_flagged_order_actions(self, mock_order_service, action, expected_order_status):
        service, mocks = mock_order_service
        mock_payment = MagicMock(id=10, status="pending")
        mock_order = MagicMock(id=10, status="pending_review", payments=[mock_payment])
        mocks["order_repo"].get_by_id.return_value = mock_order
        if action == "reject":
            mocks["payment_service"].get_payment.return_value = mock_payment
        order = service.review_flagged_order(mock_order.id, action)
        assert order.status == expected_order_status
        mocks["session"].commit.assert_called_once()
        if action == "reject":
            assert mock_payment.status == "rejected"

    @pytest.mark.parametrize("fraud_risk", [
        pytest.param("high", id="high_risk_of_fraud"),
        pytest.param("medium", id="medium_risk_of_fraud"),
        pytest.param("low", id="low_to_no_risk_of_fraud")
    ])
    def test_create_order_api_response(self, mock_order_service, checkout_data, fraud_risk):
        service, mocks = mock_order_service
        mock_product = MagicMock(name="Product", price=Decimal("20.00"), stock=10)
        mock_item = MagicMock(product=mock_product, quantity=3)
        mock_cart = MagicMock(user_id=1, items=[mock_item])

        ship_address = MagicMock(id=10)
        mocks["ship_address_repo"].get_existing_address.return_value = ship_address
        bill_address = MagicMock(id=10)
        mocks["bill_address_repo"].get_existing_address.return_value = bill_address

        mocks["fraud_service"].check_fraud.return_value = {"risk_assessment": fraud_risk}

        order = service.create_order(mock_cart, checkout_data)
        if fraud_risk == "high":
            assert order.status == "rejected"
        else:
            assert order
            if fraud_risk == "medium":
                assert order.status == "pending_review"

