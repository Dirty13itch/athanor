FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY src/ ./src/

RUN pip install --no-cache-dir .

EXPOSE 9200

CMD ["python", "-m", "gpu_orchestrator.main"]
