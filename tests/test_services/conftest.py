from datetime import datetime, UTC
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services import OrderService, PaymentService, FraudService, CartService


@pytest.fixture
def mock_cart_service():
    mocks = {
        "cart_repo": MagicMock(),
        "cart_item_repo": MagicMock(),
        "product_repo": MagicMock(),
        "order_service": MagicMock(),
        "payment_service": MagicMock(),
        "session": MagicMock(),
    }
    service = CartService(**mocks)
    return service, mocks


@pytest.fixture
def mock_order_service():
    mocks = {
        "order_repo": MagicMock(),
        "order_item_repo":  MagicMock(),
        "ship_address_repo": MagicMock(),
        "bill_address_repo": MagicMock(),
        "payment_service": MagicMock(),
        "fraud_service": MagicMock(),
        "refund_repo": MagicMock(),
        "session": MagicMock(),
    }
    service = OrderService(**mocks)
    return service, mocks


@pytest.fixture
def mock_payment_service():
    mocks = {
        "cart_item_repo": MagicMock(),
        "order_repo": MagicMock(),
        "payment_repo": MagicMock(),
        "refund_repo": MagicMock(),
        "session": MagicMock(),
    }
    service = PaymentService(**mocks)
    return service, mocks


@pytest.fixture
def mock_fraud_service():
    mocks = {
        "order_repo": MagicMock()
    }
    service = FraudService(**mocks)
    return service, mocks


@pytest.fixture
def order():
    user = SimpleNamespace(
        id=10,
        created_at=datetime.now(UTC)
    )
    return SimpleNamespace(
        id=100,
        user_id=10,
        total_amount=100.99,
        user=user
    )

@pytest.fixture
def checkout_data():
    return {
        "shipping_address": {
            "country": "United States"
        },
        "billing_same_as_shipping": True,
        "billing_address": None
    }