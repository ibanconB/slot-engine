# ============================================================
# Makefile — atajos para el proyecto slot-engine
# ============================================================

# Variables
COMPOSE := docker compose
DEV := $(COMPOSE) run --rm dev
IMAGE_DEV := slot-engine:dev
IMAGE_PROD := slot-engine:latest

# Objetivo por defecto: mostrar ayuda
.DEFAULT_GOAL := help

.PHONY: help build build-prod shell test lint format typecheck check clean fix demo

help:  ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

build:  ## Construye la imagen de desarrollo
	$(COMPOSE) build dev

build-prod:  ## Construye la imagen de producción (runtime)
	docker build --target runtime -t $(IMAGE_PROD) .

shell:  ## Abre una shell interactiva en el contenedor dev
	$(DEV) bash

test:  ## Ejecuta los tests con pytest
	$(DEV) pytest

lint:  ## Ejecuta ruff para detectar problemas
	$(DEV) ruff check .

format:  ## Aplica formato con ruff
	$(DEV) ruff format .

typecheck:  ## Verifica tipos con mypy
	$(DEV) mypy src

check: lint typecheck test  ## Ejecuta lint + typecheck + test (lo que hace CI)

clean:  ## Elimina caches y contenedores huérfanos
	$(COMPOSE) down --remove-orphans
	docker image rm -f $(IMAGE_DEV) $(IMAGE_PROD) 2>/dev/null || true
	find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache .mypy_cache build dist *.egg-info

fix:  ## Aplica fixes automáticos de ruff
	$(DEV) ruff check . --fix
	$(DEV) ruff format .

demo:
	docker compose run --rm dev slot-engine play lucky_sevens --seed 42