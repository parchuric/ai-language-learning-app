# Deploy AI Language Learning App to Azure Container Instances
# This approach bypasses App Service quota limitations

# Build and push container to Azure Container Registry, then deploy to ACI

Write-Host "🚀 Deploying AI Language Learning App using Azure Container Instances..." -ForegroundColor Green

# Configuration
$resourceGroupName = "ai-language-app-rg"
$containerGroupName = "ailangapp-container"
$acrName = "ailangappregistry" # Must be globally unique
$imageName = "ai-language-app"
$location = "eastus"

# Check if logged in to Azure
$account = az account show 2>$null
if (-not $account) {
    Write-Host "❌ Please log in to Azure CLI first: az login" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Azure CLI authenticated" -ForegroundColor Green

# Create Azure Container Registry
Write-Host "📦 Creating Azure Container Registry..." -ForegroundColor Yellow
$acrResult = az acr create --resource-group $resourceGroupName --name $acrName --sku Basic --admin-enabled true 2>$null

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Azure Container Registry created: $acrName" -ForegroundColor Green
} else {
    Write-Host "ℹ️ Container Registry might already exist, continuing..." -ForegroundColor Yellow
}

# Get ACR login server
$acrLoginServer = az acr show --name $acrName --resource-group $resourceGroupName --query "loginServer" --output tsv

# Build and push Docker image
Write-Host "🔨 Building Docker image..." -ForegroundColor Yellow

# Create Dockerfile
$dockerfileContent = @"
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Expose port
EXPOSE 8000

# Set environment variables
ENV STREAMLIT_SERVER_PORT=8000
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Create Streamlit config
RUN mkdir -p ~/.streamlit && \
    echo '[server]' > ~/.streamlit/config.toml && \
    echo 'port = 8000' >> ~/.streamlit/config.toml && \
    echo 'address = "0.0.0.0"' >> ~/.streamlit/config.toml && \
    echo 'headless = true' >> ~/.streamlit/config.toml && \
    echo 'enableCORS = false' >> ~/.streamlit/config.toml && \
    echo 'enableXsrfProtection = false' >> ~/.streamlit/config.toml

# Run the application
CMD ["python", "-m", "streamlit", "run", "app/main.py", "--server.port", "8000", "--server.address", "0.0.0.0", "--server.headless", "true"]
"@

$dockerfileContent | Out-File -FilePath "Dockerfile" -Encoding UTF8

Write-Host "✅ Dockerfile created" -ForegroundColor Green

# Build the image
docker build -t ${imageName} .

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Docker image built successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Docker build failed" -ForegroundColor Red
    exit 1
}

# Log in to ACR
Write-Host "🔑 Logging in to Azure Container Registry..." -ForegroundColor Yellow
az acr login --name $acrName

# Tag and push image
$fullImageName = "${acrLoginServer}/${imageName}:latest"
docker tag ${imageName} $fullImageName
docker push $fullImageName

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Image pushed to ACR: $fullImageName" -ForegroundColor Green
} else {
    Write-Host "❌ Image push failed" -ForegroundColor Red
    exit 1
}

# Get ACR credentials
$acrUsername = az acr credential show --name $acrName --query "username" --output tsv
$acrPassword = az acr credential show --name $acrName --query "passwords[0].value" --output tsv

# Deploy to Azure Container Instances
Write-Host "☁️ Deploying to Azure Container Instances..." -ForegroundColor Yellow

# Create the container group with environment variables
az container create `
    --resource-group $resourceGroupName `
    --name $containerGroupName `
    --image $fullImageName `
    --registry-login-server $acrLoginServer `
    --registry-username $acrUsername `
    --registry-password $acrPassword `
    --dns-name-label $containerGroupName `
    --ports 8000 `
    --memory 2 `
    --cpu 1 `
    --os-type Linux `
    --environment-variables`
        AZURE_OPENAI_ENDPOINT="https://ailangapp-openai.openai.azure.com/" `
        AZURE_OPENAI_DEPLOYMENT_NAME="gpt-4o" `
        AZURE_SPEECH_REGION="eastus" `
        KEY_VAULT_URI="https://ailangapp-kv.vault.azure.net/" `
        AZURE_SPEECH_KEY_SECRET_NAME="ailangapp-speech-key" `
        AZURE_CONTENT_SAFETY_ENDPOINT="https://eastus.api.cognitive.microsoft.com/" `
        APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=6bcc01c1-bca9-4193-b183-c6ef39d9b4c3;IngestionEndpoint=https://eastus-8.in.applicationinsights.azure.com/;LiveEndpoint=https://eastus.livediagnostics.monitor.azure.com/;ApplicationId=28b1b856-be68-4810-8f28-fa425e7e1a29"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Container deployed successfully!" -ForegroundColor Green
    
    # Get the FQDN
    $fqdn = az container show --resource-group $resourceGroupName --name $containerGroupName --query "ipAddress.fqdn" --output tsv
    Write-Host "🌐 Your app is available at: http://${fqdn}:8000" -ForegroundColor Cyan
    
    # Show container logs
    Write-Host "📊 Container logs:" -ForegroundColor Yellow
    az container logs --resource-group $resourceGroupName --name $containerGroupName
    
} else {
    Write-Host "❌ Container deployment failed" -ForegroundColor Red
    exit 1
}

# Clean up local files
Remove-Item "Dockerfile" -ErrorAction SilentlyContinue

Write-Host "🎉 Deployment complete!" -ForegroundColor Green
Write-Host "📋 Summary:" -ForegroundColor Cyan
Write-Host "  - Container Registry: $acrLoginServer" -ForegroundColor White
Write-Host "  - Container Group: $containerGroupName" -ForegroundColor White
Write-Host "  - Public URL: http://${fqdn}:8000" -ForegroundColor White
