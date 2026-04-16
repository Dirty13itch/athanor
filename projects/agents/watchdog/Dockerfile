FROM python:3.12-slim

# openssh-client for SSH probes + remediation
RUN apt-get update && \
    apt-get install -y --no-install-recommends openssh-client ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py catalog.py remediation.py circuit.py /app/

EXPOSE 9301

ENV PYTHONUNBUFFERED=1
ENV WATCHDOG_PORT=9301

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9301", "--log-level", "info"]
