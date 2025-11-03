FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Copy the requirements from the correct location within the build context
COPY slice_api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r ./requirements.txt

COPY slice_api/main.py ./
COPY slice_api/models.py ./

# Default command
CMD ["python", "main.py"]