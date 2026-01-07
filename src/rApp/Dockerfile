FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Copy the requirements from the correct location within the build context
COPY rApp/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY rApp/rApp.py ./
COPY rApp/tools.py ./
COPY rApp/config ./config
COPY rApp/utils ./utils

# Default command
CMD ["python", "main.py"]