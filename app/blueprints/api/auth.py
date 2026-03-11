from flask_jwt_extended import jwt_required, current_user
from flask_smorest import Blueprint

from app.extensions import limiter
from app.schemas.users import UserSchemas
from app.services.helpers import get_user_service
from app.utils.responses import api_response

api_auth_bp = Blueprint(
    "api_auth",
    __name__,
    url_prefix="/api/auth",
    description="User authentication and authorization",
)


@api_auth_bp.route("/register", methods=["POST"])
@api_auth_bp.doc(security=[])
@limiter.limit("3 per minute")
@api_auth_bp.arguments(UserSchemas.Create)
@api_auth_bp.response(201, UserSchemas.AuthResponse)
def register_user(user_data):
    """Register a new user account."""
    service = get_user_service()
    new_user, access_token, refresh_token = service.register_user(user_data)
    return api_response(
        status_code=201,
        message="User successfully registered.",
        data={
            "user": UserSchemas.Public().dump(new_user),
            "access_token": access_token,
            "refresh_token": refresh_token,
        }
    )


@api_auth_bp.route("/login", methods=["POST"])
@api_auth_bp.doc(security=[])
@limiter.limit("5 per minute")
@api_auth_bp.arguments(UserSchemas.Login)
@api_auth_bp.response(200, UserSchemas.AuthResponse)
def login_user(login_credentials):
    """Authenticate an existing user and issue access and refresh tokens."""
    service = get_user_service()
    user, access_token, refresh_token = service.login_user(login_credentials)
    return api_response(
        message="User successfully logged in.",
        data={
            "user": UserSchemas.Public().dump(user),
            "access_token": access_token,
            "refresh_token": refresh_token,
        }
    )


@api_auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
@limiter.limit("10 per minute")
@api_auth_bp.response(200, UserSchemas.AuthResponse)
def refresh_tokens():
    """Refresh tokens using a valid refresh token."""
    service = get_user_service()
    user, access_token, refresh_token = service.refresh_session(current_user)
    return api_response(
        message="Session refreshed.",
        data={
            "user": UserSchemas.Public().dump(user),
            "access_token": access_token,
            "refresh_token": refresh_token,
        }
    )


@api_auth_bp.route("/me")
@jwt_required()
@api_auth_bp.response(200, UserSchemas.PublicResponse)
def get_current_user():
    """Retrieve the current logged-in user's profile information."""
    return api_response(
        message="Your profile",
        data=UserSchemas.Public().dump(current_user)
    )


@api_auth_bp.route("/update_profile", methods=["PATCH"])
@jwt_required()
@api_auth_bp.arguments(UserSchemas.Update)
@api_auth_bp.response(200, UserSchemas.PublicResponse)
def update_profile(user_data):
    """Update the current logged-in user's profile details."""
    service = get_user_service()
    updated_user = service.update_user(
        user=current_user,
        user_data=user_data
    )
    return api_response(
        message="Profile updated.",
        data=UserSchemas.Public().dump(updated_user)
    )