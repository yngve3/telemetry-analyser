FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY telemetry-source/backend/pyproject.toml telemetry-source/backend/README.md ./telemetry-source/backend/
COPY telemetry-source/backend/src ./telemetry-source/backend/src
COPY shared-contracts ./shared-contracts

RUN pip install --no-cache-dir --no-build-isolation ./telemetry-source/backend

EXPOSE 8000
EXPOSE 14540/udp

CMD ["uvicorn", "telemetry_source_backend.presentation.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
