import os
from typing import Optional, Union

from fakeredis import FakeRedis
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, get_jwt_identity
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate
from flask_smorest import Api, ErrorHandlerMixin
from flask_sqlalchemy import SQLAlchemy
from redis import Redis
from sqlalchemy.orm import DeclarativeBase

from app.schemas.responses import ApiResponseSchema


class Base(DeclarativeBase):
    pass


class CustomApi(Api, ErrorHandlerMixin):
    ERROR_SCHEMA = ApiResponseSchema


def user_key():
    """rate limiter by user instead of IP"""
    try:
        identity = get_jwt_identity()
    except RuntimeError:
        identity = None
    return identity or get_remote_address()


redis_client: Optional[Union[FakeRedis, Redis]] = None
def init_redis(app):
    global redis_client
    if app.config["REDIS_URL"]:
        redis_client = Redis.from_url(os.getenv("REDIS_URL"))
    else:
        redis_client = FakeRedis()

    app.redis_client = redis_client

db = SQLAlchemy(model_class=Base)
ma = Marshmallow()
jwt = JWTManager()
migrate = Migrate()
bcrypt = Bcrypt()
limiter = Limiter(
    key_func=user_key,
    storage_uri="memory://",
    default_limits=["50 per hour", "200 per day"],
)
api = CustomApi()

