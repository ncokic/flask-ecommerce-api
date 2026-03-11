from datetime import datetime, UTC, timedelta
from unittest.mock import MagicMock

import pytest

from app.utils.error_handlers import ServiceError


class TestPaymentService:
    @pytest.mark.parametrize("event, payment_status, order_status, stock_deducted", [
        pytest.param("success", "accepted", "paid", True, id="successful_payment_event"),
        pytest.param("failure", "rejected", "pending", False, id="unsuccessful_payment_event"),
    ])
    def test_payment_webhook(self, mock_payment_service, event, payment_status, order_status, stock_deducted):
        service, mocks = mock_payment_service
        mock_product = MagicMock(stock=5)
        mock_item = MagicMock(product=mock_product, quantity=2)
        mock_order = MagicMock(status="pending", items=[mock_item])
        mock_payment = MagicMock(id=1, status="pending", order=mock_order)
        mocks["payment_repo"].get_by_id.return_value = mock_payment
        mocks["payment_repo"].save.return_value = mock_payment

        payment = service.payment_webhook(payment_id=mock_payment.id, event=event)
        assert payment.status == payment_status
        assert payment.order.status == order_status

        product = payment.order.items[0].product
        if stock_deducted:
            assert product.stock == 3
            mocks["cart_item_repo"].clear_cart_items.assert_called_once()
        else:
            assert product.stock == 5

        mocks["session"].commit.assert_called_once()

    @pytest.mark.parametrize("order_status", ["pending", "shipped"])
    def test_refund_request_rejected_invalid_order_status(self, mock_payment_service, order_status):
        service, mocks = mock_payment_service
        mock_order = MagicMock(id=1, status=order_status)
        mocks["order_repo"].get_user_order.return_value = mock_order

        with pytest.raises(ServiceError) as e:
            service.send_refund_request(user_id=1, order_id=mock_order.id, reason="wrong_item")

        assert e.value.status_code == 409
        if mock_order.status == "pending":
            assert "not yet shipped" in e.value.message.lower()
        else:
            assert "wait for delivery" in e.value.message.lower()

    @pytest.mark.parametrize("days, should_fail", [
        pytest.param(8, True, id="refund_window_expired"),
        pytest.param(6, False, id="refund_window_active"),
    ])
    def test_refund_request_refund_window(self, mock_payment_service, days, should_fail):
        service, mocks = mock_payment_service
        mock_order = MagicMock(id=1, status="delivered", delivered_at=datetime.now(UTC)-timedelta(days=days))
        mocks["order_repo"].get_user_order.return_value = mock_order

        if should_fail:
            with pytest.raises(ServiceError) as e:
                service.send_refund_request(user_id=1, order_id=mock_order.id, reason="not_as_described")
            assert e.value.status_code == 409
            assert "window expired" in e.value.message.lower()
            mocks["refund_repo"].create_refund_request.assert_not_called()

        else:
            mock_refund_request = MagicMock(order_id=mock_order.id, status="pending")
            mock_order.refund_request = mock_refund_request
            mocks["refund_repo"].create_refund_request.return_value = mock_refund_request
            order = service.send_refund_request(user_id=1, order_id=1, reason="not_as_described")
            assert order.refund_request.status == "pending"
            mocks["session"].commit.assert_called_once()

    @pytest.mark.parametrize("refund_accepted, reason, order_returned, expected_status", [
        pytest.param(True, "wrong_item", True, "accepted", id="admin_accepts_refund_request_wrong_item"),
        pytest.param(True, "damaged_item", True, "accepted", id="admin_accepts_refund_damaged_item"),
        pytest.param(False, "not_as_described", False, "rejected", id="admin_rejects_refund_request"),
    ])
    def test_refund_request_handling(
            self, mock_payment_service, refund_accepted, reason, order_returned, expected_status
    ):
        service, mocks = mock_payment_service
        mock_product = MagicMock(stock=5)
        mock_item = MagicMock(product=mock_product, quantity=2)
        mock_refund_request = MagicMock(status="pending", reason=reason)
        mock_order = MagicMock(id=1, refund_request=mock_refund_request, items=[mock_item])
        mocks["order_repo"].get_by_id.return_value = mock_order

        order = service.handle_refund_request(
            order_id=mock_order.id,
            refund_accepted=refund_accepted,
            order_returned=order_returned,
        )
        assert order.refund_request.status == expected_status
        refund = order.refund_request
        if refund.status == "accepted":
            if order_returned and refund.reason != "damaged_item":
                assert mock_product.stock == 7
            else:
                assert mock_product.stock == 5

        mocks["session"].commit.assert_called_once()