# Trusted, prebuilt runtime image. Build and pin this image before enabling hosted scoring.
FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PYTHONPATH=/opt/higgslab/src
RUN apt-get update && apt-get install -y --no-install-recommends bash \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/higgslab
COPY evaluator/requirements-sandbox.txt ./requirements-sandbox.txt
RUN python -m pip install --no-cache-dir -r requirements-sandbox.txt
RUN python -m pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.9.0
COPY src/higgslab ./src/higgslab
USER 65534:65534
WORKDIR /submission
