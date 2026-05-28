FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY analysis-module/pyproject.toml analysis-module/README.md ./analysis-module/
COPY analysis-module/src ./analysis-module/src

COPY telemetry-converter/pyproject.toml telemetry-converter/README.md ./telemetry-converter/
COPY telemetry-converter/src ./telemetry-converter/src

COPY analysis-service/pyproject.toml analysis-service/README.md ./analysis-service/
COPY analysis-service/src ./analysis-service/src

RUN pip install --no-cache-dir --no-build-isolation \
    ./analysis-module \
    ./telemetry-converter \
    ./analysis-service

EXPOSE 8010
EXPOSE 14560/udp

CMD ["uvicorn", "analysis_service.presentation.api.app:app", "--host", "0.0.0.0", "--port", "8010"]
