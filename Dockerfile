FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy project files
COPY . .

# Install dependencies
RUN pip install \
    fastapi \
    uvicorn \
    httpx \
    pydantic \
    pydantic-settings \
    chromadb \
    sentence-transformers \
    numpy \
    pandas \
    redis \
    loguru \
    python-jose[cryptography] \
    openpyxl

# Create logs directory
RUN mkdir -p logs

# Expose port
EXPOSE 8000

# Default command
CMD ["python", "-m", "orchestrator.main"]

# In Dockerfile, add:
RUN pip install google-generativeai
