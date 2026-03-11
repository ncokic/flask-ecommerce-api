import json
import os

import click
from flask import current_app
from flask.cli import with_appcontext
from flask_migrate import upgrade, stamp

from app.enums import UserRole
from app.extensions import db, redis_client
from app.models import Product
from app.repositories import UserRepository
from app.schemas.users import UserSchemas
from config import BASE_DIR


def register_cli_commands(app):
    app.cli.add_command(make_admin_command)
    app.cli.add_command(seed_db_command)
    app.cli.add_command(reset_db_command)
    app.cli.add_command(clear_keys_command)
    app.cli.add_command(setup_command)

def make_admin(email):
    user_repo = UserRepository(session=db.session)
    user = user_repo.get_by_email(email)
    if not user:
        click.echo(f"User {email} not found.")
        return

    if click.confirm("Are you sure?"):
        if user.role == UserRole.ADMIN:
            click.echo(f"User {email} is already an admin.")
        else:
            user.role = UserRole.ADMIN
            db.session.commit()
            click.echo(f"User {email} is now an admin.")
    else:
        click.echo("Command cancelled")

def reset_db(bypass=False):
    if bypass or click.confirm("This will delete the current database and recreate it. Are you sure?"):
        db.drop_all()
        stamp(revision="base")
        upgrade()
        click.echo("Database recreated at the latest version.")
    else:
        click.echo("Command cancelled.")

def seed_db():
    click.echo("Seeding database... (this may take a few seconds due to password hashing)")
    users_file = BASE_DIR / "seeds" / "users.json"
    with open(users_file) as file:
        users = json.load(file)

    for user_data in users:
        # seeding through user schema because of password hashing set up through model+schema
        user = UserSchemas.Seed().load(user_data)
        db.session.add(user)

    products_file = BASE_DIR / "seeds" / "products.json"
    with open(products_file) as file:
        products = json.load(file)

    for product_data in products:
        product = Product(**product_data)
        db.session.add(product)

    db.session.commit()
    click.echo("Database seeded successfully.")

def clear_keys():
    redis = getattr(current_app, "redis_client", None)
    if redis:
        redis.flushall()
        click.echo("Idempotency keys cleared.")
    else:
        click.echo("Redis client not yet initialized. Skipping key clearance.")


@click.command("make-admin")
@click.argument("email")
@with_appcontext
def make_admin_command(email):
    """Make user an admin."""
    make_admin(email)


@click.command("reset-db")
@with_appcontext
def reset_db_command():
    """Delete all current database data and create new database."""
    reset_db()


@click.command("seed-db")
@with_appcontext
def seed_db_command():
    """Seed database with provided users and products data."""
    seed_db()


@click.command("clear-keys")
@with_appcontext
def clear_keys_command():
    """Clear all idempotency keys from Redis."""
    clear_keys()


@click.command("setup")
@with_appcontext
def setup_command():
    """Automate the entire environment setup."""
    reset_db(bypass=True)
    seed_db()
    clear_keys()
    if os.getenv("DATABASE_URL"):
        click.echo("Setup complete. Dockerized API is ready at http://localhost:5050")
    else:
        click.echo("Setup complete. Use 'flask run' to start the server.")