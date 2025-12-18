ifneq (,$(wildcard .env))
include .env
export
endif

.PHONY: help venv install run docker-build docker-run docker-down logs \
        test test-unit test-integration coverage lint format clean health tree

TAG ?= graph-api:dev
PYTHON ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip
PY := $(VENV)/bin/python

API_URL = http://localhost
NEO4J_BOLT ?= bolt://localhost:7687

help:
	@echo "Commands:"
	@echo "  make venv              Create local virtualenv (.venv)"
	@echo "  make install            Install dependencies locally"
	@echo "  make run                Run API locally (uvicorn)"
	@echo "  make docker-build       Build Docker image (TAG=$(TAG))"
	@echo "  make docker-run         Start stack with docker compose"
	@echo "  make docker-down        Stop stack"
	@echo "  make logs               Follow API logs"
	@echo "  make health             Check /health, /openapi.json, and Neo4j bolt"
	@echo "  make test               Run all tests (unit + integration)"
	@echo "  make test-unit          Run only unit tests"
	@echo "  make test-integration   Run only integration tests"
	@echo "  make coverage           Run tests with coverage report"
	@echo "  make lint               Run pylint"
	@echo "  make format             Run black"
	@echo "  make clean              Remove caches"
	@echo "  make tree               Show project tree (depth 3)"

# -----------------------
# Local python workflow
# -----------------------
venv:
	@test -d $(VENV) || $(PYTHON) -m venv $(VENV)
	@$(PY) -m pip install -U pip setuptools wheel

install: venv
	@$(PIP) install -r requirements.txt
	@# optional: if you have a dev requirements file, keep it; otherwise install common dev tools:
	@$(PIP) install -q pytest pytest-cov httpx pylint black || true

run: venv
	@$(PY) -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# -----------------------
# Docker workflow
# -----------------------

wait-neo4j:
	@echo "⏳ Waiting for Neo4j (bolt ready)..."
	@for i in $$(seq 1 60); do \
		if docker compose exec -T neo4j cypher-shell -u neo4j -p "$$NEO4J_PASSWORD" "RETURN 1;" >/dev/null 2>&1; then \
			echo "✅ Neo4j is ready"; \
			exit 0; \
		fi; \
		sleep 2; \
	done; \
	echo "❌ Neo4j not ready after 120s"; \
	exit 1

seed:
	@echo "🌱 Seeding Neo4j (safe to re-run)..."
	@docker compose exec -T api python scripts/seed_data.py

docker-build:
	docker build -t $(TAG) .

docker-run:
	docker compose up -d --build
	@$(MAKE) wait-neo4j
	@$(MAKE) seed

docker-down:
	docker compose down -v

logs:
	docker compose logs -f api

# -----------------------
# Health checks (rubric)
# -----------------------
health:
	@echo "Checking API /health ..."
	@curl -sf $(API_URL)/health >/dev/null && echo "✅ /health OK" || (echo "❌ /health FAIL" && exit 1)
	@echo "Checking API /openapi.json ..."
	@curl -sf $(API_URL)/openapi.json >/dev/null && echo "✅ /openapi.json OK" || (echo "❌ /openapi.json FAIL" && exit 1)
	@echo "Checking Neo4j bolt ($(NEO4J_BOLT)) ..."
	@docker compose exec -T neo4j cypher-shell -u $(NEO4J_USER) -p "$(NEO4J_PASSWORD)" "RETURN 1;" >/dev/null \
		&& echo "✅ Neo4j bolt OK" || (echo "❌ Neo4j bolt FAIL (check NEO4J_PASSWORD)" && exit 1)

# -----------------------
# Tests
# -----------------------
test: test-unit test-integration

test-unit: install
	@NEO4J_URI=bolt://localhost:7687 API_URL=http://localhost $(PY) -m pytest -q -m "not integration"

test-integration: install
	@NEO4J_URI=bolt://localhost:7687 API_URL=http://localhost $(PY) -m pytest -q -m integration

coverage: venv
	@API_URL=$(API_URL) \
	NEO4J_URI=bolt://localhost:7687 \
	NEO4J_USER=$(NEO4J_USER) \
	NEO4J_PASSWORD=$(NEO4J_PASSWORD) \
	$(PY) -m pytest -q --cov=app --cov-report=term-missing --cov-report=html
	@echo "✅ Coverage HTML report generated in ./htmlcov/index.html"


# -----------------------
# Quality
# -----------------------
lint: venv
	@$(PY) -m pylint app || true

format: venv
	@$(PY) -m black app tests -l 120 || true

clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} \; || true
	find . -type f -name "*.pyc" -delete || true
	rm -rf .pytest_cache .coverage htmlcov

tree:
	@if command -v tree >/dev/null 2>&1; then \
		tree -L 3 -I "node_modules|dist|.git|.venv|__pycache__|htmlcov"; \
	else \
		find . -maxdepth 3 -type d -not -path '*/\.*' | sort; \
	fi
