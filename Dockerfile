# Stage 1: Builder stage (handles dependencies and credentials)
FROM python:3.10-slim AS builder

# Install system dependencies (git and openssh-client for SSH)
RUN apt-get update && apt-get install -y --no-install-recommends git openssh-client && \
    rm -rf /var/lib/apt/lists/*


# Configure SSH: Trust GitHub's host key
RUN mkdir -p /root/.ssh && \
    chmod 700 /root/.ssh && \
    ssh-keyscan -t rsa,ecdsa,ed25519 github.com >> /root/.ssh/known_hosts && \
    chmod 600 /root/.ssh/known_hosts

# Install UV
COPY --from=ghcr.io/astral-sh/uv:0.5.20 /uv /usr/local/bin/uv

# Create project directory structure
WORKDIR /app

# Copy project files
COPY communication ./communication
COPY data_model_fboot ./data_model_fboot
COPY opc_ua ./opc_ua
COPY core ./core
COPY resources ./resources
COPY pyproject.toml ./
COPY uv.lock ./

# Install dependencies using UV sync with pyproject.toml
RUN --mount=type=ssh uv sync --frozen --verbose

# Stage 2: Final stage (clean image without credentials)
FROM python:3.10-slim

# Copy the application from the builder
COPY --from=builder /app /app

# Set the working directory
WORKDIR /app

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code (excluding unnecessary files)
COPY communication ./communication
COPY data_model_fboot ./data_model.fboot
COPY opc_ua ./opc_ua
COPY core ./core
COPY resources ./resources
COPY resources/data_model.fboot_default ./resources/data_model.fboot

# Start dinasore
ENTRYPOINT [ "python", "core/main.py"]
