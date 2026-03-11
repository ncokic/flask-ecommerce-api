from app.extensions import db
from app.repositories import UserRepository


def register_jwt_auth_handlers(jwt):
    @jwt.user_identity_loader
    def user_identity_loader(user):
        return str(user.id)

    @jwt.user_lookup_loader
    def user_lookup_callback(_header, data):
        user_id = data["sub"]
        user_repo = UserRepository(db.session)
        return user_repo.get_by_id(user_id)