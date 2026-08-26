FROM python:3.11-slim@sha256:7b7f6b0b7cf8b7a9ce7ec7e2bdcb55f01d7f3ad5dd5a65caf9f975eab7dc3a49

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

USER 65532:65532
EXPOSE 8080
CMD ["python", "-m", "omp.server", "--cloud-http", "--host", "0.0.0.0", "--port", "8080"]
