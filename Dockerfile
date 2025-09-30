FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY falai_mcp /app/falai_mcp

RUN pip install --no-cache-dir .

EXPOSE 8080

CMD ["falai-mcp"]
