.PHONY: help setup install run lint format clean

# Detect uv executable
UV := $(shell command -v ~/.local/bin/uv 2> /dev/null || command -v uv 2> /dev/null)

help:
	@echo "========================================================================"
	@echo "                       HealthBridge Makefile                            "
	@echo "========================================================================"
	@echo "Available commands:"
	@echo "  setup, install  Install all dependencies and set up virtual environment"
	@echo "  run             Run the main HealthBridge demonstration script"
	@echo "  lint            Lint the codebase using Ruff"
	@echo "  format          Format codebase using Black and Ruff (auto-fixing)"
	@echo "  clean           Clean up temporary cache files and virtual environment"
	@echo "========================================================================"

setup: install

install:
	@if [ -z "$(UV)" ]; then \
		echo "Error: 'uv' is not installed or not in PATH."; \
		echo "Please install uv: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Installing dependencies and setting up virtual environment..."
	$(UV) sync

run:
	@if [ ! -f ".env" ]; then \
		echo "[!] Error: .env file is missing."; \
		echo "Please copy .env.example to .env and fill in your credentials."; \
		exit 1; \
	fi
	$(UV) run python main.py

lint:
	$(UV) run ruff check .

format:
	$(UV) run black .
	$(UV) run ruff check --fix .

clean:
	@echo "Cleaning up temporary files..."
	rm -rf .venv
	rm -rf .ruff_cache
	rm -rf .mypy_cache
	rm -rf .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.py[co]" -delete
	@echo "To also delete Garmin Connect cache tokens, run: rm -rf .garminconnect"
