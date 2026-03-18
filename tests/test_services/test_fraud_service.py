from unittest.mock import MagicMock, patch
import httpx
import pytest


class TestFraudService:
    def test_check_fraud_success(self, mock_fraud_service, order, checkout_data):
        service = mock_fraud_service[0]
        mock_response = MagicMock()
        mock_response.json.return_value = {"risk_assessment": "low"}

        with patch("httpx.Client.post", return_value=mock_response):
            with patch.object(service, "gather_data", return_value={"some": "data"}):
                response = service.check_fraud(order, checkout_data)

        assert response == {"risk_assessment": "low"}

    @pytest.mark.parametrize("exception", [
        httpx.ConnectTimeout("Connection Timeout"),
        httpx.ReadTimeout("Processing Timeout"),
        httpx.HTTPStatusError(
            "Server Error",
            request=httpx.Request(method="POST", url="http://test"),
            response=httpx.Response(500)
        ),
        httpx.RequestError("Network Error")
    ])
    def test_check_fraud_service_down(self, mock_fraud_service, order, checkout_data, exception):
        service = mock_fraud_service[0]
        with patch("httpx.Client.post", side_effect=exception):
            with patch.object(service, "gather_data", return_value={"some": "data"}):
                response = service.check_fraud(order, checkout_data)

        assert response["risk_assessment"] == "low"
        assert "fraud check skipped" in response["risk_score"].lower()

    def test_gather_data(self, mock_fraud_service, order, checkout_data):
        service, mocks = mock_fraud_service
        with patch("country_converter.convert", return_value="US"), \
             patch("ipapi.location", return_value={"country": "US"}):

            mocks["order_repo"].count_user_orders_last_24h.return_value = 2
            response = service.gather_data(order, checkout_data, client_ip="8.8.8.8")

        assert response["orders_last_24h"] == 2
        assert response["is_shipping_billing_mismatch"] == False
        assert response["shipping_country"] == "US"
        assert response["ip_country"] == "US"