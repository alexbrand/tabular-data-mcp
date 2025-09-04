# Use the official uv image to build dependencies
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

# Set environment variables for uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Install dependencies
WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy the application
ADD . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Use a minimal Python image for the final stage
FROM python:3.11-slim-bookworm

# Install deno (required for mcp-run-python sandbox)
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Deno
ENV DENO_INSTALL=/usr/local
RUN curl -fsSL https://deno.land/x/install/install.sh | sh

# Copy the application from the builder
COPY --from=builder --chown=app:app /app /app

# Create data directory and set permissions
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app && \
    mkdir -p /app/data && \
    chown app:app /app/data

# Switch to non-root user
USER app

# Ensure the virtual environment is in the path
ENV PATH="/app/.venv/bin:$PATH"

# Change to the application directory
WORKDIR /app

# Expose the data directory as a volume
VOLUME ["/app/data"]

# Expose port 8000 for SSE mode
EXPOSE 8000

# Run the MCP server
CMD ["python", "main.py"]
