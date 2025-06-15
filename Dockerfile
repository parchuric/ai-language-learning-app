FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Expose port
EXPOSE 8000

# Set environment variables for production
ENV STREAMLIT_SERVER_PORT=8000
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Create Streamlit config directory and file
RUN mkdir -p ~/.streamlit && \
    echo '[server]' > ~/.streamlit/config.toml && \
    echo 'port = 8000' >> ~/.streamlit/config.toml && \
    echo 'address = "0.0.0.0"' >> ~/.streamlit/config.toml && \
    echo 'headless = true' >> ~/.streamlit/config.toml && \
    echo 'enableCORS = false' >> ~/.streamlit/config.toml && \
    echo 'enableXsrfProtection = false' >> ~/.streamlit/config.toml && \
    echo '[browser]' >> ~/.streamlit/config.toml && \
    echo 'gatherUsageStats = false' >> ~/.streamlit/config.toml

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8000/_stcore/health || exit 1

# Run the application
CMD ["python", "-m", "streamlit", "run", "app/main.py", "--server.port", "8000", "--server.address", "0.0.0.0", "--server.headless", "true"]
