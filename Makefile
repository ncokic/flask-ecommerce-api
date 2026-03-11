.PHONY: help up down nuke setup logs test db-shell db-list-users db-dump

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  up         Build and start containers in background"
	@echo "  down       Stop and remove containers"
	@echo "  nuke       Stop and remove containers and volumes"
	@echo "  setup      Run database migrations and seed data"
	@echo "  test       Run pytest suite inside the web container"
	@echo "  logs       Logs for the web service"
	@echo "  db-shell   Open a Postgres shell inside the db container"

up:
    docker-compose up --build -d

down:
    docker-compose down

nuke:
    docker-compose down -v

setup:
    docker-compose exec web flask setup

logs:
    docker-compose logs -f web

test:
    docker-compose exec web pytest

db-shell:
    docker-compose exec db psql -U hello_flask -d ecommerce_prod

db-list-users:
	docker-compose exec db psql -U hello_flask -d ecommerce_prod -c "SELECT username, email, role FROM users;"

db-dump:
	docker-compose exec db pg_dump -U hello_flask ecommerce_prod > backup.sql