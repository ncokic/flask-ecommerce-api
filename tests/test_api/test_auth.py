from unittest.mock import patch

import pytest
from flask_jwt_extended import decode_token
from sqlalchemy import select

from app.extensions import db, limiter
from app.models import User

REGISTRATION_PAYLOAD = {
    "username": "user",
    "email": "user@test.com",
    "password": "user123"
}


class TestAuth:
    @pytest.mark.parametrize("key, value, expected_response", [
        pytest.param("username", "test_user", 201, id="valid_request_payload"),
        pytest.param("username", "", 422, id="empty_request_field"),
        pytest.param("email", "bad_email", 422, id="invalid_email_form"),
        pytest.param("password", "123", 422, id="password_too_short"),
        pytest.param("username", "x" * 200, 422, id="username_too_long")
    ])
    def test_register_user_validation(self, client, key, value, expected_response):
        with patch.object(limiter, "enabled", False):
            initial_count = len(db.session.execute(select(User)).scalars().all())
            payload = REGISTRATION_PAYLOAD | {key: value}
            response = client.post("/api/auth/register", json=payload)
            assert response.status_code == expected_response
            current_count = len(db.session.execute(select(User)).scalars().all())
            if response.status_code == 201:
                assert current_count == initial_count + 1
            else:
                assert current_count == initial_count

    @pytest.mark.parametrize("key, value", [
        pytest.param("username", "new_user", id="email_already_exists"),
        pytest.param("email", "newuser@email.com", id="username_already-exists"),
    ])
    def test_registration_data_already_exists(self, client, test_user, key, value):
        with patch.object(limiter, "enabled", False):
            payload = REGISTRATION_PAYLOAD | {key: value}
            response = client.post("/api/auth/register", json=payload)
            assert response.status_code == 409
            assert "already exist" in response.get_json()["message"].lower()

    def test_register_password_hashing(self, client):
        payload = REGISTRATION_PAYLOAD
        response = client.post("/api/auth/register", json=payload)
        assert response.status_code == 201

        user = db.session.execute(
            select(User)
            .where(User.email == "user@test.com")
        ).scalars().first()

        assert user is not None
        assert user.password_hash != payload["password"]
        assert len(user.password_hash) > 20

    def test_registration_limiter(self, client):
        register_limit = 3 # per minute
        for i in range(register_limit + 1):
            payload = {
                "username": f"user_{i}",
                "email": f"user_{i}@test.com",
                "password": "user123",
            }
            response = client.post("api/auth/register", json=payload)
            if i < register_limit:
                assert response.status_code == 201
            else:
                assert response.status_code == 429

    @pytest.mark.parametrize("email, password, expected_status", [
        pytest.param("user@test.com", "user123", 200, id="valid_login_request"),
        pytest.param("bad_email@test.com", "user123", 401, id="invalid_email"),
        pytest.param("user@test.com", "bad_password", 401, id="invalid_password"),
    ])
    def test_user_login(self, client, test_user, email, password, expected_status):
        with patch.object(limiter, "enabled", False):
            payload = {
                "email": email,
                "password": password,
            }
            response = client.post("/api/auth/login", json=payload)
            assert response.status_code == expected_status
            if response.status_code == 200:
                data = response.get_json()["data"]
                decoded_access = decode_token(data["access_token"])
                decoded_refresh = decode_token(data["refresh_token"])

                assert data["user"]["email"] == test_user["email"]
                assert str(decoded_access["sub"]) == str(test_user["id"])
                assert str(decoded_refresh["sub"]) == str(test_user["id"])

    @pytest.mark.parametrize("token, expected_response", [
        pytest.param("refresh_token", 200, id="valid_token_provided"),
        pytest.param("access_token", 401, id="invalid_token_provided"),
    ])
    def test_refresh_session(self, client, test_user, token, expected_response):
        with patch.object(limiter, "enabled", False):
            headers = {
                "Authorization": f"Bearer {test_user[token]}"
            }
            response = client.post("/api/auth/refresh", headers=headers)
            assert response.status_code == expected_response
            if response.status_code == 200:
                data = response.get_json()["data"]
                decoded_access = decode_token(data["access_token"])
                assert str(decoded_access["sub"]) == str(test_user["id"])

    @pytest.mark.parametrize("token, expected_status", [
        pytest.param("access_token", 200, id="valid_access_token"),
        pytest.param("bad_token", 401, id="invalid_access_token"),
        pytest.param("", 401, id="missing_access_token"),
    ])
    def test_token_auth_on_get_current_user(self, client, test_user, token, expected_status):
        if token != "":
            headers = \
                {"Authorization": f"Bearer {test_user[token]}"} \
                if token == "access_token" \
                else {"Authorization": f"Bearer {token}"}
        else:
            headers = ""

        response = client.get("/api/auth/me", headers=headers)
        assert response.status_code == expected_status
        if response.status_code == 200:
            data = response.get_json()["data"]
            assert data["email"] == test_user["email"]
        else:
            message = response.get_json()["message"].lower()
            if token == "bad_token":
                assert "invalid" in message
            else:
                assert "missing" in message

    def test_update_user_profile(self, client, test_user):
        payload = {"username": "updated_user", "password": "updated123"}
        response = client.patch(
            "/api/auth/update_profile",
            json=payload,
            headers=test_user["headers"])
        assert response.status_code == 200

        data = response.get_json()["data"]
        assert data["username"] == payload["username"]
        assert data["email"] == test_user["email"]

        login_payload = {
            "email": data["email"],
            "password": payload["password"]
        }
        response = client.post("/api/auth/login", json=login_payload)
        assert response.status_code == 200
        data = response.get_json()["data"]
        decoded_access = decode_token(data["access_token"])
        assert str(decoded_access["sub"]) == str(test_user["id"])
