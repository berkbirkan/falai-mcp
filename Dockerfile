FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FALAI_ENABLE_HTTP=true \
    FALAI_HTTP_HOST=0.0.0.0 \
    FALAI_HTTP_PORT=18888 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install build tools
RUN pip install --upgrade pip setuptools wheel

# Copy requirements first for better caching
COPY pyproject.toml requirements.txt /app/

# Install Python dependencies with compatibility resolution
RUN pip install --no-cache-dir --no-deps . && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY falai_mcp /app/falai_mcp

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

EXPOSE 18888

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:18888/mcp/ || exit 1

CMD ["falai-mcp"]
