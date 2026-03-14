.PHONY: build up down logs test lint migrate seed health

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

logs-nlp:
	docker compose logs -f nlp_service

migrate:
	docker compose exec postgres psql -U $${POSTGRES_USER:-news_user} -d news_ai -f /dev/stdin < scripts/migrate.sql

seed:
	docker compose exec nlp_service python scripts/seed_sources.py

health:
	@echo "Postgres:" && docker compose exec postgres pg_isready -U $${POSTGRES_USER:-news_user} 2>/dev/null && echo "OK" || echo "FAIL"
	@echo "Redis:" && docker compose exec redis redis-cli ping 2>/dev/null || echo "FAIL"
	@echo "Qdrant:" && curl -sf http://localhost:6333/healthz && echo " OK" || echo "FAIL"
	@echo "NLP:" && curl -sf http://localhost:8081/health && echo " OK" || echo "FAIL"

test:
	cd services/nlp_py && python -m pytest tests/ -v

restart-nlp:
	docker compose restart nlp_service
