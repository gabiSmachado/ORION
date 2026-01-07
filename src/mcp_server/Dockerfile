###############################
# MCP Server Dockerfile
# Build from repository root: (inside intent-mcp/src)
#   docker build -f mcp_server/Dockerfile -t mcp_server .
###############################

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first (better layer caching)
COPY mcp_server/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy server code & supporting assets
COPY mcp_server/server.py ./
COPY mcp_server/config ./config
COPY mcp_server/utils ./utils

# Default command
CMD ["python", "server.py"]