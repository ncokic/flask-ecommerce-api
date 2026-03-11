import hashlib
import hmac
import json
import re
from functools import wraps

from flask import request, current_app
from flask_jwt_extended import jwt_required, get_jwt

from app.enums import UserRole
from .error_handlers import ServiceError
from .responses import api_response

KEY_EXPIRATION = 24 * 60 * 60  # 1 day
UUID_REGEX_FORMAT = re.compile(
    r"^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$", re.I
)


def hash_request_data():
    """Hashes request body data to solve same key/different request conflict."""
    data = request.get_data(as_text=True)
    to_hash = f"{request.method}:{request.path}:{data}".encode()
    return hashlib.sha256(to_hash).hexdigest()

def idempotent_route(fn):
    """Decorator for implementing idempotency to routes."""
    @wraps(fn)
    def enhanced_fn(*args, **kwargs):
        if request.method not in ("POST", "PUT", "PATCH"):
            return fn(*args, **kwargs)

        redis = getattr(current_app, "redis_client", None)

        key = request.headers.get("Idempotency-Key")
        if not key:
            raise ServiceError(400, "Idempotency-Key required.")

        if not UUID_REGEX_FORMAT.match(key):
            raise ServiceError(400, "Invalid Idempotency-Key format. UUID4 format required.")

        hashed_data = hash_request_data()
        raw_value = redis.get(key)
        if raw_value:
            cached_value = json.loads(raw_value.decode())

            # check if duplicate request
            if cached_value["status"] == "in_progress":
                raise ServiceError(409, "Request already in progress")

            # check if request body matches the key
            if cached_value["hash"] != hashed_data:
                raise ServiceError(400, "Request body and key mismatch")

            return api_response(
                    message="Request already processed",
                    data=cached_value["data"],
                )

        redis.set(
            key,
            json.dumps({"status": "in_progress", "hash": hashed_data}),
            nx=True,
            ex=60,
        )

        try:
            response = fn(*args, **kwargs)
            payload = {
                "status": "completed",
                "hash": hashed_data,
                "status_code": response.status_code,
                "data": response.get_json().get("data"),
            }
            redis.set(key, json.dumps(payload), ex=KEY_EXPIRATION)
            return response

        except Exception:
            # delete key if unexpected crash so user is not locked out
            redis.delete(key)
            raise

    return enhanced_fn


def admin_only(fn):
    """Decorator function for admin access."""
    @wraps(fn)
    @jwt_required()
    def enhanced_fn(*args, **kwargs):
        claims = get_jwt()
        if claims.get("role") != UserRole.ADMIN:
            raise ServiceError(403, "Admin access required.")
        return fn(*args, **kwargs)
    return enhanced_fn


def signature_required(fn):
    @wraps(fn)
    def enhanced_fn(*args, **kwargs):
        signature = request.headers.get("X-Signature")
        if not signature:
            raise ServiceError(401, "X-Signature header required.")

        secret_key = current_app.config.get("WEBHOOK_SECRET_KEY")

        data = request.get_json()
        normalized_data = json.dumps(
            data,
            separators=(",", ":"),
            sort_keys=True,
        )

        expected_signature = hmac.new(
            key=secret_key.encode(),
            msg=normalized_data.encode(),
            digestmod=hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected_signature, signature):
            raise ServiceError(401, "Invalid signature.")

        return fn(*args, **kwargs)
    return enhanced_fn