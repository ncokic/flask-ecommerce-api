from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def mock_ipapi():
    with patch("app.services.fraud_service.ipapi.location") as mocked_response:
        mocked_response.return_value = {"country": "US"}
        yield mocked_response


@pytest.fixture(autouse=True)
def mock_fraud_check_api_call():
    with patch("app.services.fraud_service.FraudService.check_fraud") as mocked_response:
        mocked_response.return_value = {
            "risk_assessment": "low",
            "risk_score": 10
        }
        yield mocked_response