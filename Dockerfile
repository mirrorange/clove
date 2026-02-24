# Multi-stage Dockerfile for Clove (uv version)

# =============================================================================
# Stage 1: Build frontend
# =============================================================================
FROM node:20-alpine AS frontend-builder

# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app/front

# Copy frontend package files
COPY front/package.json front/pnpm-lock.yaml ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy frontend source
COPY front/ ./

# Build frontend
RUN pnpm run build

# =============================================================================
# Stage 2: Build Python application with uv
# =============================================================================
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS app

# uv optimization environment variables
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Step 1: Copy dependency files only (leverage Docker layer caching)
COPY pyproject.toml uv.lock ./

# Install dependencies (without installing the project itself)
# --locked: Use lockfile for consistency
# --no-install-project: Only install dependencies, not the project
# --no-dev: Skip dev dependencies
# --extra rnet --extra curl: Install optional dependency groups
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev --extra rnet --extra curl

# Step 2: Copy application code and README.md (required by pyproject.toml)
COPY app/ ./app/
COPY README.md ./

# Step 3: Copy frontend build artifacts (required by pyproject.toml force-include)
COPY --from=frontend-builder /app/front/dist ./app/static

# Step 4: Install the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --extra rnet --extra curl

# Create data directory
RUN mkdir -p /data

# Activate virtual environment (add .venv/bin to PATH)
ENV PATH="/app/.venv/bin:$PATH"

# Environment variables
ENV DATA_FOLDER=/data \
    HOST=0.0.0.0 \
    PORT=5201

# Expose port
EXPOSE 5201

# Reset ENTRYPOINT (uv image default is uv)
ENTRYPOINT []

# Run the application
CMD ["python", "-m", "app.main"]
