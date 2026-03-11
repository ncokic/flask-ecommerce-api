from enum import Enum


class BaseEnum(str, Enum):
    @classmethod
    def get_enum_values(cls, enum_class):
        return [item.value for item in enum_class]


class UserRole(BaseEnum):
    ADMIN = "admin"
    USER = "user"


class OrderStatus(BaseEnum):
    PENDING = "pending"
    PAID = "paid"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentStatus(BaseEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class RefundStatus(BaseEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class RefundReason(BaseEnum):
    NOT_AS_DESCRIBED = "not_as_described"
    WRONG_ITEM = "wrong_item"
    DAMAGED_ITEM = "damaged_item"
    OTHER = "other"
    CANCELLED_ORDER = "cancelled_order"


class ProductSortOptions(BaseEnum):
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"
    NAME_ASC = "name_asc"
    NAME_DESC = "name_desc"


class OrderSortOptions(BaseEnum):
    TOTAL_ASC = "total_asc"
    TOTAL_DESC = "total_desc"
    OLDEST = "oldest"
    NEWEST = "newest"


class UserSortOptions(BaseEnum):
    NAME_ASC = "name_asc"
    NAME_DESC = "name_desc"
    OLDEST = "oldest"
    NEWEST = "newest"
