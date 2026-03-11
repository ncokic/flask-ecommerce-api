from flask_limiter.errors import RateLimitExceeded
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException

from app.utils.responses import api_response


class ServiceError(Exception):
    """Custom error handler for services"""
    def __init__(self, status_code, message):
        super().__init__()
        self.status_code = status_code
        self.message = message


def register_error_handlers(app):
    @app.errorhandler(ServiceError)
    def handle_custom_api_error(error: ServiceError):
        return api_response(
            success=False,
            status_code=error.status_code,
            message=error.message,
        )

    @app.errorhandler(ValidationError)
    def handle_validation_error(error: ValidationError):
        return api_response(
            success=False,
            status_code=422,
            message="Validation failed.",
            data=error.messages,
        )

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        return api_response(
            success=False,
            status_code=error.code,
            message=error.description,
        )

    @app.errorhandler(RateLimitExceeded)
    def handle_rate_limit_error(error: RateLimitExceeded):
        return api_response(
            success=False,
            status_code=429,
            message=f"Too many requests. Limit: {error.description}",
        )

    @app.errorhandler(IntegrityError)
    def handle_integrity_error(error:IntegrityError):
        return api_response(
            success=False,
            status_code=409,
            message="Database conflict.",
        )

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        app.logger.exception(f"Unhandled exception: {str(error)}")
        return api_response(
            success=False,
            status_code=500,
            message="Internal server error.",
        )


def register_jwt_errors(jwt):
    @jwt.expired_token_loader
    def handle_expired_token(header, data):
        return api_response(
            success=False,
            status_code=401,
            message="Token expired. Please log in again."
        )

    @jwt.invalid_token_loader
    def handle_invalid_token(error):
        return api_response(
            success=False,
            status_code=401,
            message="Invalid token. Verification failed."
        )

    @jwt.unauthorized_loader
    def handle_unauthorized(error):
        return api_response(
            success=False,
            status_code=401,
            message="Request is missing an access token."
        )

    @jwt.user_lookup_error_loader
    def handle_user_lookup_error(header, data):
        return api_response(
            success=False,
            status_code=401,
            message="User associated with this token no longer exists."
        )
