from flask_smorest import Blueprint

from app.schemas.products import ProductSchemas
from app.services.helpers import get_product_service, split_query_args
from app.utils.responses import api_response
from app.utils.security import admin_only

api_products_bp = Blueprint(
    "api_products",
    __name__,
    url_prefix="/api/products",
    description="Product management endpoints",
)


@api_products_bp.route("")
@api_products_bp.doc(security=[])
@api_products_bp.arguments(ProductSchemas.Query, location="query")
@api_products_bp.response(200, ProductSchemas.ListPublicResponse)
def list_products(args):
    """Retrieve a list of products, supports optional pagination, filtering and sorting."""
    service = get_product_service()
    page, per_page, filters, sort = split_query_args(args)
    products, total = service.get_products(
        page=page,
        per_page=per_page,
        filters=filters,
        sort=sort,
    )
    return api_response(data={
        "products": ProductSchemas.Public(many=True).dump(products),
        "total": total,
        "page": page,
        "per_page": per_page,
    })


@api_products_bp.route("", methods=["POST"])
@admin_only
@api_products_bp.arguments(ProductSchemas.Admin)
@api_products_bp.response(201, ProductSchemas.AdminResponse)
def create_product(product_data):
    """Create a new product (admin only)."""
    service = get_product_service()
    new_product = service.create_product(product_data)
    return api_response(
        status_code=201,
        message=f"{new_product.name} added to inventory.",
        data=ProductSchemas.Admin().dump(new_product),
    )


@api_products_bp.route("/<int:product_id>")
@api_products_bp.doc(security=[])
@api_products_bp.response(200, ProductSchemas.PublicResponse)
def get_product(product_id):
    """Retrieve details for a specific product."""
    service = get_product_service()
    product = service.get_product_by_id(product_id)
    return api_response(data=ProductSchemas.Public().dump(product))


@api_products_bp.route("/<int:product_id>", methods=["PATCH"])
@admin_only
@api_products_bp.arguments(ProductSchemas.Update(partial=True))
@api_products_bp.response(200, ProductSchemas.AdminResponse)
def update_product(product_data, product_id):
    """Update information for a specific product (admin only)."""
    service = get_product_service()
    updated_product = service.update_product(product_id, product_data)
    return api_response(
        message=f"{updated_product.name} updated.",
        data=ProductSchemas.Admin().dump(updated_product)
    )


@api_products_bp.route("/<int:product_id>", methods=["DELETE"])
@admin_only
@api_products_bp.response(200, ProductSchemas.AdminResponse)
def delete_product(product_id):
    """Delete a product from the database (admin only)."""
    service = get_product_service()
    service.delete_product(product_id)
    return api_response(message=f"Product {product_id} deleted.")