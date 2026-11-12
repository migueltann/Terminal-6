# Terminal-6 container image
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first so Docker can cache this layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code, tests and web assets
COPY *.py pytest.ini ./
COPY ai/ ai/
COPY filtering/ filtering/
COPY models/ models/
COPY storage/ storage/
COPY user_io/ user_io/
COPY tests/ tests/
COPY templates/ templates/
COPY static/ static/

# Directory for saved recommendation data
RUN mkdir -p /app/data /app/instance

# Document the Flask web port
EXPOSE 5000

# Default: run the terminal application
CMD ["python", "main.py"]