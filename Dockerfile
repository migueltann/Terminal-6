# Terminal-6 container image
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first so Docker can cache this layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code and the tests
COPY *.py pytest.ini ./
COPY tests/ tests/
COPY templates/ templates/
COPY static/ static/

# Saved recommendation sets are written here (mount a volume to keep them)
RUN mkdir -p /app/data

# Default: run the terminal application
CMD ["python", "main.py"]