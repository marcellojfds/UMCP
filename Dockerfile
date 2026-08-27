FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app
COPY pyproject.toml README.md alembic.ini ./
COPY src ./src
COPY migrations ./migrations
RUN pip install --no-cache-dir .

USER 65532:65532
EXPOSE 8080
CMD ["python", "-m", "omp.server", "--cloud-http", "--host", "0.0.0.0", "--port", "8080"]
