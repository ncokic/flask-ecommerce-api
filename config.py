import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

load_dotenv()

class Config:
    FLASK_APP = os.getenv("FLASK_APP")
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///./ecommerce.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WEBHOOK_SECRET_KEY = os.getenv("WEBHOOK_SECRET_KEY")
    REDIS_URL = os.getenv("REDIS_URL", None)

    #JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=60)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)

    #Flask-Smorest/OpenAPI
    API_TITLE = "eCommerce App"
    API_VERSION = "v1"
    OPENAPI_VERSION = "3.1.0"
    OPENAPI_URL_PREFIX = "/api/docs"
    OPENAPI_SWAGGER_UI_PATH = "/swagger"
    OPENAPI_SWAGGER_UI_URL = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
    API_DEFAULT_ERROR_RESPONSE_NAME = "GlobalErrorResponse"
    API_DOCS_URL = OPENAPI_URL_PREFIX + OPENAPI_SWAGGER_UI_PATH

    #Flask-Smorest custom options
    API_SPEC_OPTIONS = {
        "security": [{"bearerAuth": []}],
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                },
            }
        },
        "errors": {"422": "UnprocessableEntity"},
    }


class DevelopmentConfig(Config):
    DEBUG = True
    # SQLALCHEMY_ECHO = True


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    BCRYPT_LOG_ROUNDS = 4
    SECRET_KEY = os.getenv("TEST_FLASK_SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("TEST_JWT_SECRET_KEY")
    WEBHOOK_SECRET_KEY = os.getenv("TEST_WEBHOOK_SECRET_KEY")
