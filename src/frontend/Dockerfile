###############################
# MCP Frontend Dockerfile
# Build from intent/src directory:
#   docker build -f frontend/Dockerfile -t frontend .
###############################

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 

WORKDIR /app

# Install deps
COPY frontend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy frontend code and any config directory
COPY frontend/chatbot.py ./
COPY frontend/main.py ./
COPY frontend/config ./config
COPY frontend/utils ./utils

# Optionally copy an env file if present at build time (won't break if absent)
# Commented out by default to avoid baking secrets into the image.
# COPY .env ./.env

# Default execution (interactive intent input expected on stdin)
EXPOSE 8500

CMD ["streamlit", "run", "main.py"]
