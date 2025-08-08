.PHONY: help build test lint clean proto-gen migrate seed up down logs

# Default target
help:
	@echo "Available commands:"
	@echo "  build      - Build all services"
	@echo "  test       - Run all tests"
	@echo "  lint       - Run linting for all services"
	@echo "  proto-gen  - Generate gRPC stubs"
	@echo "  migrate    - Run database migrations"
	@echo "  seed       - Seed database with initial data"
	@echo "  up         - Start all services with Docker Compose"
	@echo "  down       - Stop all services"
	@echo "  logs       - Show logs from all services"
	@echo "  clean      - Clean build artifacts and containers"

# Build all services
build:
	@echo "Building all services..."
	docker-compose build --parallel

# Test all services
test:
	@echo "Running tests..."
	cd services/api_go && go test ./...
	cd services/ingester_go && go test ./...
	cd services/nlp_py && python -m pytest tests/
	cd frontend && npm test

# Lint all services
lint:
	@echo "Running linting..."
	cd services/api_go && golangci-lint run
	cd services/ingester_go && golangci-lint run
	cd services/nlp_py && flake8 . && mypy .
	cd frontend && npm run lint

# Generate gRPC stubs
proto-gen:
	@echo "Generating gRPC stubs..."
	./scripts/proto_gen.sh

# Database operations
migrate:
	@echo "Running database migrations..."
	docker-compose exec postgres psql -U $$POSTGRES_USER -d $$POSTGRES_DB -f /docker-entrypoint-initdb.d/migrate.sql

seed:
	@echo "Seeding database..."
	python scripts/bootstrap_db.py

# Docker Compose operations
up:
	@echo "Starting all services..."
	docker-compose up -d

down:
	@echo "Stopping all services..."
	docker-compose down

logs:
	@echo "Showing logs..."
	docker-compose logs -f

# Development
dev-api:
	cd services/api_go && go run cmd/api/main.go

dev-ingester:
	cd services/ingester_go && go run cmd/ingester/main.go

dev-nlp:
	cd services/nlp_py && python app/server.py

dev-frontend:
	cd frontend && npm run dev

# Clean up
clean:
	@echo "Cleaning up..."
	docker-compose down -v --remove-orphans
	docker system prune -f
	cd services/api_go && go clean
	cd frontend && rm -rf .next node_modules

# Health checks
health:
	@echo "Checking service health..."
	curl -f http://localhost:8080/health || echo "API Gateway: DOWN"
	curl -f http://localhost:8081/health || echo "NLP Service: DOWN"
	curl -f http://localhost:6333/health || echo "Qdrant: DOWN"

# Install dependencies
install:
	@echo "Installing dependencies..."
	cd services/api_go && go mod download
	cd services/ingester_go && go mod download
	cd services/nlp_py && pip install -r requirements.txt
	cd frontend && npm install

# Format code
fmt:
	@echo "Formatting code..."
	cd services/api_go && go fmt ./...
	cd services/ingester_go && go fmt ./...
	cd services/nlp_py && black . && isort .
	cd frontend && npm run format 