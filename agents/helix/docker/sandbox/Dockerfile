FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl build-essential nodejs npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

CMD ["bash"]
