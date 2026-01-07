###############################
# MCP Client Dockerfile
# Build from intent-mcp/src directory:
#   docker build -f mcp_client/Dockerfile -t mcp_client .
###############################

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install deps (use service-specific requirements)
COPY mcp_client/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy client code and any config directory
COPY mcp_client/client.py ./
COPY mcp_client/main.py ./
COPY mcp_client/config ./config
COPY mcp_client/utils ./utils

# Optionally copy an env file if present at build time (won't break if absent)
# Commented out by default to avoid baking secrets into the image.
# COPY .env ./.env

# Default execution (interactive intent input expected on stdin)
CMD ["python", "main.py"]
