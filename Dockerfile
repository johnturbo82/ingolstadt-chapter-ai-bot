FROM node:20-bookworm-slim

# GitHub Copilot CLI benötigt Node.js, das Skript selbst läuft mit Python.
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g @github/copilot

RUN pip3 install --break-system-packages --no-cache-dir requests

WORKDIR /app
COPY create_and_publish.py SKILL.md ./

ENTRYPOINT ["python3", "create_and_publish.py"]
