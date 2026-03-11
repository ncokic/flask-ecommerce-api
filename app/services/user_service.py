from flask_jwt_extended import create_access_token, create_refresh_token
from sqlalchemy.orm import Session

from app.repositories import UserRepository
from app.utils.error_handlers import ServiceError


class UserService:
    def __init__(self, repo: UserRepository, session: Session):
        self.repo = repo
        self.session = session

    def get_users(self, page=None, per_page=None, filters=None, sort=None):
        query = self.repo.select_all()

        if filters:
            query = self.repo.apply_filters(query, filters)

        if sort:
            query = self.repo.apply_sorting(query, sort)

        if page and per_page:
            paginated = self.repo.paginate_users(query, page, per_page)
            return paginated.items, paginated.total

        users = self.repo.get_all_users(query)
        total = len(users)
        return users, total


    def get_user_by_id(self, user_id):
        user = self.repo.get_by_id(user_id)
        if not user:
            raise ServiceError(404, "User not found")
        return user

    def register_user(self, user_data):
        username = self.repo.get_by_username(user_data.username)
        email = self.repo.get_by_email(user_data.email)
        if username or email:
            raise ServiceError(409, "Username or email already exist")

        new_user = self.repo.save(user_data)
        self.session.commit()
        self.session.refresh(new_user)

        access_token, refresh_token = self.create_tokens(new_user)
        return new_user, access_token, refresh_token

    def login_user(self, credentials):
        user = self.repo.get_by_email(credentials["email"])
        if not user or not user.check_password(credentials["password"]):
            raise ServiceError(401, "Invalid username or password")

        access_token, refresh_token = self.create_tokens(user)
        return user, access_token, refresh_token

    def update_user(self, user, user_data):
        for key, value in user_data.items():
            setattr(user, key, value)
        self.session.commit()
        self.session.refresh(user)
        return user

    def refresh_session(self, user):
        new_access_token, new_refresh_token = self.create_tokens(user)
        return user, new_access_token, new_refresh_token

    def create_tokens(self, user):
        access_token = create_access_token(
            identity=user,
            additional_claims={"role": user.role},
        )
        refresh_token = create_refresh_token(identity=user)
        return access_token, refresh_token