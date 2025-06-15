#!/bin/bash

# Startup script for Azure App Service
# This script sets up and runs the Streamlit application

echo "🚀 Starting AI Language Learning App on Azure App Service..."

# Set environment variables for production
export PYTHONPATH="${PYTHONPATH}:/home/site/wwwroot"

# Install dependencies if needed (App Service should handle this via requirements.txt)
echo "📦 Installing Python dependencies..."
python -m pip install --upgrade pip
pip install -r requirements.txt

# Set Streamlit configuration for production
export STREAMLIT_SERVER_PORT=8000
export STREAMLIT_SERVER_ADDRESS=0.0.0.0
export STREAMLIT_SERVER_HEADLESS=true
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Create Streamlit config directory if it doesn't exist
mkdir -p ~/.streamlit

# Create Streamlit config file for production
cat > ~/.streamlit/config.toml << EOF
[server]
port = 8000
address = "0.0.0.0"
headless = true
enableCORS = false
enableXsrfProtection = false

[browser]
gatherUsageStats = false

[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
EOF

echo "✅ Environment configured for production"

# Start the Streamlit application
echo "🌟 Starting Streamlit application..."
cd /home/site/wwwroot
streamlit run app/main.py --server.port 8000 --server.address 0.0.0.0 --server.headless true
