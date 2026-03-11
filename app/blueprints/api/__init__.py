from .admin import api_admin_bp
from .auth import api_auth_bp
from .cart import api_cart_bp
from .orders import api_orders_bp
from .payments import api_payments_bp
from .products import api_products_bp

BLUEPRINTS = [api_admin_bp, api_auth_bp, api_products_bp,
              api_cart_bp,api_orders_bp, api_payments_bp]

def register_blueprints(api):
    for blueprint in BLUEPRINTS:
        api.register_blueprint(blueprint)

    api.spec.components.response(
        "GlobalErrorResponse", {
            "description": "Standard error response",
            "content": {
                "application/json": {
                    "schema": "ApiResponseSchema"
                }
            }
        }
    )