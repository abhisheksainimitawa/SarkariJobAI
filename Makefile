install:
	pip install -r apps/api/requirements.txt -r scripts/requirements.txt && \
	pip install -e packages/schema && \
	cd apps/web && npm install

db-start:
	docker compose -f infra/docker-compose.yml up -d postgres

db-migrate:
	cd db && alembic upgrade head

db-reset:
	cd db && alembic downgrade base && alembic upgrade head

api:
	cd apps/api && uvicorn main:app --reload --port 8000

web:
	cd apps/web && npm run dev

dev:
	make db-start && make api & make web

test-api:
	pytest tests/api -v

test-scripts:
	pytest tests/scripts -v

test-web:
	cd apps/web && npm run test

test-all:
	make test-api && make test-scripts && make test-web
