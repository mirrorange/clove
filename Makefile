.PHONY: help build build-frontend build-wheel install install-dev clean run test

# Default target
help:
	@echo "Available commands:"
	@echo "  make build          - Build frontend and create Python wheel"
	@echo "  make build-frontend - Build only the frontend"
	@echo "  make build-wheel    - Build only the Python wheel"
	@echo "  make install        - Build and install the package"
	@echo "  make install-dev    - Install in development mode"
	@echo "  make clean          - Clean build artifacts"
	@echo "  make run            - Run the application (development)"
	@echo "  make test           - Run tests"

# Build everything
build:
	@python scripts/build_wheel.py

# Build only frontend
build-frontend:
	@cd front && pnpm install && pnpm run build
	@rm -rf app/static
	@cp -r front/dist app/static
	@echo "✓ Frontend build complete"

# Build only wheel
build-wheel:
	@python scripts/build_wheel.py --skip-frontend

# Build and install
install: build
	@pip install dist/*.whl
	@echo "✓ Clove installed successfully"
	@echo "Run 'clove' to start the application"

# Install in development mode
install-dev:
	@pip install -e .
	@echo "✓ Clove installed in development mode"

# Clean build artifacts
clean:
	@rm -rf dist build *.egg-info
	@rm -rf app/__pycache__ app/**/__pycache__
	@rm -rf .pytest_cache .ruff_cache
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@echo "✓ Cleaned build artifacts"

# Run the application (development mode)
run:
	@python -m app.main