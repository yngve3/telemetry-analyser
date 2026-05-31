FROM node:24-bookworm-slim

ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PATH="/opt/static-analysis/venv/bin:/opt/static-analysis/node_modules/.bin:/root/go/bin:${PATH}"
ENV NODE_PATH="/opt/static-analysis/node_modules"

WORKDIR /opt/static-analysis

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        python3 \
        python3-pip \
        python3-venv \
    && rm -rf /var/lib/apt/lists/*

COPY tools/static-analysis/requirements.txt ./requirements.txt
RUN python3 -m venv /opt/static-analysis/venv \
    && pip install --upgrade pip \
    && pip install -r requirements.txt

COPY tools/static-analysis/package.json ./package.json
RUN npm install

ARG GITLEAKS_VERSION=8.30.1
RUN curl -fsSL \
        "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" \
        -o /tmp/gitleaks.tar.gz \
    && tar -xzf /tmp/gitleaks.tar.gz -C /usr/local/bin gitleaks \
    && chmod +x /usr/local/bin/gitleaks \
    && rm /tmp/gitleaks.tar.gz

WORKDIR /workspace

ENTRYPOINT ["bash"]
CMD ["./tools/static-analysis/scripts/run-all.sh"]
