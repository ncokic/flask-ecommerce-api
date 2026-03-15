from sqlalchemy import select, delete, func
from sqlalchemy.orm import Session, joinedload, selectinload

from app.extensions import db
from app.models import Product, User, Cart, CartItem, ShippingAddress, Order, OrderItem, Payment, Refund, BillingAddress


class BaseRepository:
    model = None

    def __init__(self, session: Session):
        self.session = session

    def get_all(self, query=None):
        if query is None:
            query = select(self.model)
        result = self.session.execute(query)
        return result.scalars().all()

    def get_by_id(self, obj_id):
        return self.session.get(self.model, obj_id)

    def save(self, obj):
        """Used for both create and update"""
        if isinstance(obj, dict):
            new_instance = self.model(**obj)
            self.session.add(new_instance)
            return new_instance
        else:
            self.session.add(obj)
            return obj

    def remove(self, obj):
        self.session.delete(obj)

    def select_all(self):
        return select(self.model)


class UserRepository(BaseRepository):
    model = User

    def get_all_users(self, query):
        result = self.session.execute(
            query.options(
            joinedload(self.model.cart)
            .selectinload(Cart.items)
            .joinedload(CartItem.product),
            selectinload(self.model.orders)
            .joinedload(Order.refund_request)
        ))
        return result.scalars().all()

    def get_by_username(self, username):
        result = self.session.execute(
            select(self.model)
            .where(func.lower(self.model.username) == username.lower())
        )
        return result.scalars().first()

    def get_by_email(self, email):
        result = self.session.execute(
            select(self.model)
            .where(func.lower(self.model.email) == email.lower())
        )
        return result.scalars().first()

    def apply_filters(self, query, filters):
        for key, value in filters.items():
            if value is None:
                continue

            if key == "search_username":
                query = query.where(self.model.username.ilike(f"%{value}%"))
            elif key == "search_email":
                query = query.where(self.model.email.ilike(f"%{value}%"))

        return query

    def apply_sorting(self, query, sort):
        if sort == "name_asc":
            query = query.order_by(self.model.username)
        elif sort == "name_desc":
            query = query.order_by(self.model.username.desc())
        elif sort == "oldest":
            query = query.order_by(self.model.created_at)
        elif sort == "newest":
            query = query.order_by(self.model.created_at.desc())

        return query

    def paginate_users(self, query, page, per_page):
        users = query.options(
            joinedload(self.model.cart)
            .selectinload(Cart.items)
            .joinedload(CartItem.product),
            selectinload(self.model.orders)
            .joinedload(Order.refund_request)
        )
        return db.paginate(
            users,
            page=page,
            per_page=per_page,
            error_out=False,
        )


class ProductRepository(BaseRepository):
    model = Product

    def get_by_name(self, name):
        result = self.session.execute(
            select(self.model)
            .where(self.model.name == name)
        )
        return result.scalars().first()


    def apply_filters(self, query, filters: dict):
        for key, value in filters.items():
            if value is None:
                continue

            if key == "category":
                query = query.where(func.lower(self.model.category) == value.lower())
            elif key == "min_price":
                query = query.where(self.model.price >= value)
            elif key == "max_price":
                query = query.where(self.model.price <= value)
            elif key == "in_stock":
                if value:
                    query = query.where(self.model.stock > 0)
                else:
                    query = query.where(self.model.stock == 0)
            elif key == "search":
                query = query.where(self.model.name.ilike(f"%{value}%"))

        return query

    def apply_sorting(self, query, sort):
        if sort.lower() == "price_asc":
            query = query.order_by(self.model.price)
        elif sort.lower()  == "price_desc":
            query = query.order_by(self.model.price.desc())
        elif sort.lower() == "name_asc":
            query = query.order_by(self.model.name)
        elif sort.lower() == "name_desc":
            query = query.order_by(self.model.name.desc())

        return query

    def paginate_products(self, products, page, per_page):
        return db.paginate(
            products,
            page=page,
            per_page=per_page,
            error_out=False,
        )


class CartRepository(BaseRepository):
    model = Cart

    def get_cart_by_user_id(self, user_id):
        result = self.session.execute(
            select(self.model)
            .options(
                selectinload(self.model.items)
                .joinedload(CartItem.product)
            )
            .where(self.model.user_id == user_id)
        )
        return result.scalars().first()

    def create_cart(self, user_id):
        new_cart = Cart(user_id=user_id)
        return self.save(new_cart)


class CartItemRepository(BaseRepository):
    model = CartItem

    def find_product_in_cart(self, cart_id, product_id):
        result = self.session.execute(
            select(self.model)
            .where(self.model.cart_id == cart_id)
            .where(self.model.product_id == product_id)
        )
        return result.scalars().first()

    def add_item_to_cart(self, cart_id, product_id, quantity):
        new_item = self.model(
            cart_id=cart_id,
            product_id=product_id,
            quantity=quantity,
        )
        return self.save(new_item)

    def clear_cart_items(self, cart_id):
        self.session.execute(
            delete(self.model).where(self.model.cart_id == cart_id)
        )


class OrderRepository(BaseRepository):
    model = Order

    def select_user_orders(self, user_id):
        return select(self.model).where(self.model.user_id == user_id)

    def get_all_orders(self, query):
        result = self.session.execute(
            query
            .options(
                selectinload(self.model.items).joinedload(OrderItem.product),
                joinedload(self.model.shipping_info),
                joinedload(self.model.billing_info),
                joinedload(self.model.refund_request),
            )
        )
        return result.scalars().all()

    def get_user_order(self, user_id, order_id):
        result = self.session.execute(
            select(self.model)
            .options(
                selectinload(self.model.items).joinedload(OrderItem.product),
                joinedload(self.model.shipping_info),
                joinedload(self.model.billing_info),
                joinedload(self.model.refund_request),
            )
            .where(self.model.user_id == user_id)
            .where(self.model.id == order_id)
        )
        return result.scalars().first()


    def create_order(self, user_id):
        new_order = self.model(
            user_id=user_id,
            total_amount=0,
        )
        return self.save(new_order)

    def apply_filters(self, query, filters):
        for key, value in filters.items():
            if value is None:
                continue

            if key == "status":
                query = query.where(self.model.status == value.lower())
            elif key == "min_amount":
                query = query.where(self.model.total_amount >= value)
            elif key == "max_amount":
                query = query.where(self.model.total_amount <= value)

            elif key == "user_id":
                query = query.where(self.model.user_id == value)
            elif key == "refund_status":
                query = query.where(self.model.refund_request.has(status=value))

        return query

    def apply_sorting(self, query, sort):
        if sort.lower() == "total_asc":
            query = query.order_by(self.model.total_amount)
        elif sort.lower() == "total_desc":
            query = query.order_by(self.model.total_amount.desc())
        elif sort.lower() == "oldest":
            query = query.order_by(self.model.created_at)
        elif sort.lower() == "newest":
            query = query.order_by(self.model.created_at.desc())

        return query

    def paginate_orders(self, query, page, per_page):
        orders = query.options(
            selectinload(self.model.items).joinedload(OrderItem.product),
            joinedload(self.model.shipping_info),
            joinedload(self.model.billing_info),
            joinedload(self.model.refund_request),
        )
        return db.paginate(
            orders,
            page=page,
            per_page=per_page,
            error_out=False,
        )

    def count_user_orders_last_24h(self, user_id, one_day_ago):
        return self.session.scalar(
            select(func.count())
            .select_from(self.model)
            .where(self.model.user_id == user_id)
            .where(self.model.created_at >= one_day_ago)
        )


class OrderItemRepository(BaseRepository):
    model = OrderItem

    def add_item_to_order(self, order, item):
        order_item = self.model(
            order_id=order.id,
            product_id=item.product.id,
            price=item.product.price,
            quantity=item.quantity,
        )
        return self.save(order_item)


class BaseAddressRepository(BaseRepository):
    def get_existing_address(self, address: dict):
        result = self.session.execute(
            select(self.model).filter_by(
                full_name=address["full_name"],
                street=address["street"],
                city=address["city"],
                postal_code=address["postal_code"],
                country=address["country"],
            )
        )
        return result.scalars().first()


class ShippingAddressRepository(BaseAddressRepository):
    model = ShippingAddress


class BillingAddressRepository(BaseAddressRepository):
    model = BillingAddress


class PaymentRepository(BaseRepository):
    model = Payment

    def get_payment_from_order(self, order_id):
        result = self.session.execute(
            select(self.model)
            .options(
                joinedload(self.model.order)
                .joinedload(Order.refund_request)
            )
            .where(self.model.order_id == order_id)
        )
        return result.scalars().first()

    def create_payment(self, order):
        payment = self.model(
            order_id=order.id,
            amount=order.total_amount,
        )
        return self.save(payment)


class RefundRepository(BaseRepository):
    model = Refund

    def create_refund_request(self, order_id, reason):
        refund_request = self.model(
            order_id=order_id,
            reason=reason,
        )
        return self.save(refund_request)