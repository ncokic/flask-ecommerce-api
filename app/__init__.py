from flask import Flask, redirect

from app.blueprints.api import register_blueprints
from app.extensions import db, ma, jwt, migrate, bcrypt, limiter, api, init_redis
from app.utils.auth_handlers import register_jwt_auth_handlers
from app.utils.cli_commands import register_cli_commands
from app.utils.error_handlers import register_error_handlers, register_jwt_errors
from config import DevelopmentConfig


def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.json.sort_keys = False

    db.init_app(app)
    ma.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    bcrypt.init_app(app)
    limiter.init_app(app)
    api.init_app(app)
    init_redis(app)
    from app import models

    register_blueprints(api)
    register_cli_commands(app)
    register_error_handlers(app)
    register_jwt_errors(jwt)
    register_jwt_auth_handlers(jwt)

    @app.route("/")
    def index():
        return redirect(config_class.API_DOCS_URL)

    from flask import jsonify

    @app.errorhandler(422)
    def handle_unprocessable_entity(err):
        # exc contains the marshmallow validation errors
        exc = getattr(err, "exc", None)
        if exc:
            print(f"!!! VALIDATION ERROR: {exc.messages}")
        return jsonify({"errors": exc.messages if exc else "Unprocessable Entity"}), 422

    return app