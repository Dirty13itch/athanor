FROM python:3.12-slim

# Install git for git operations in tasks
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
COPY src/ ./src/

RUN pip install --no-cache-dir . && pip install --no-cache-dir pytest

EXPOSE 9000

CMD ["python", "-m", "athanor_agents.server"]
