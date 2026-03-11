from sqlalchemy.orm import Session

from app.repositories import ProductRepository
from app.utils.error_handlers import ServiceError


class ProductService:
    def __init__(self, repo: ProductRepository, session: Session):
        self.repo = repo
        self.session = session

    def get_products(self, page=None, per_page=None, filters=None, sort=None):
        query = self.repo.select_all()

        if filters:
            query = self.repo.apply_filters(query, filters)

        if sort:
            query = self.repo.apply_sorting(query, sort)

        if page and per_page:
            paginated = self.repo.paginate_products(query, page, per_page)
            return paginated.items, paginated.total

        products = self.repo.get_all(query)
        total = len(products)
        return products, total

    def get_product_by_id(self, product_id):
        product = self.repo.get_by_id(product_id)
        if not product:
            raise ServiceError(404, "Product not found")
        return product

    def create_product(self, product_obj):
        name = self.repo.get_by_name(product_obj.name)
        if name:
            raise ServiceError(409, "Product name already exists")
        product = self.repo.save(product_obj)
        self.session.commit()
        self.session.refresh(product)
        return product

    def update_product(self, product_id, product_data):
        product = self.get_product_by_id(product_id)
        for key, value in product_data.items():
            setattr(product, key, value)
        self.session.commit()
        self.session.refresh(product)
        return product

    def delete_product(self, product_id):
        product = self.get_product_by_id(product_id)
        self.repo.remove(product)
        self.session.commit()