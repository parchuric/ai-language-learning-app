# Deploy AI Language Learning App to Azure Container Instances
# This approach bypasses App Service quota limitations

Write-Host "Deploying AI Language Learning App using Azure Container Instances..." -ForegroundColor Green

# Configuration
$resourceGroupName = "ai-language-app-rg"
$containerGroupName = "ailangapp-container"
$acrName = "ailangappregistry" # Must be globally unique
$imageName = "ai-language-app"
$location = "eastus"

# Check if logged in to Azure
Write-Host "Checking Azure CLI authentication..." -ForegroundColor Yellow
$account = az account show 2>$null
if (-not $account) {
    Write-Host "Please log in to Azure CLI first: az login" -ForegroundColor Red
    exit 1
}
Write-Host "Azure CLI authenticated" -ForegroundColor Green

# Create Azure Container Registry
Write-Host "Creating Azure Container Registry..." -ForegroundColor Yellow
$acrResult = az acr create --resource-group $resourceGroupName --name $acrName --sku Basic --admin-enabled true 2>$null

if ($LASTEXITCODE -eq 0) {
    Write-Host "Azure Container Registry created: $acrName" -ForegroundColor Green
} else {
    Write-Host "Container Registry might already exist, continuing..." -ForegroundColor Yellow
}

# Get ACR login server
Write-Host "Getting ACR login server..." -ForegroundColor Yellow
$acrLoginServer = az acr show --name $acrName --resource-group $resourceGroupName --query "loginServer" --output tsv
Write-Host "ACR Login Server: $acrLoginServer" -ForegroundColor Green

# Build Docker image
Write-Host "Building Docker image..." -ForegroundColor Yellow
docker build -t ${imageName} .

if ($LASTEXITCODE -eq 0) {
    Write-Host "Docker image built successfully" -ForegroundColor Green
} else {
    Write-Host "Docker build failed" -ForegroundColor Red
    exit 1
}

# Log in to ACR
Write-Host "Logging in to Azure Container Registry..." -ForegroundColor Yellow
az acr login --name $acrName

if ($LASTEXITCODE -eq 0) {
    Write-Host "Logged in to ACR successfully" -ForegroundColor Green
} else {
    Write-Host "ACR login failed" -ForegroundColor Red
    exit 1
}

# Tag and push image
Write-Host "Tagging and pushing image to ACR..." -ForegroundColor Yellow
$fullImageName = "${acrLoginServer}/${imageName}:latest"
docker tag ${imageName} $fullImageName
docker push $fullImageName

if ($LASTEXITCODE -eq 0) {
    Write-Host "Image pushed to ACR: $fullImageName" -ForegroundColor Green
} else {
    Write-Host "Image push failed" -ForegroundColor Red
    exit 1
}

# Get ACR credentials
Write-Host "Getting ACR credentials..." -ForegroundColor Yellow
$acrUsername = az acr credential show --name $acrName --query "username" --output tsv
$acrPassword = az acr credential show --name $acrName --query "passwords[0].value" --output tsv

# Deploy to Azure Container Instances
Write-Host "Deploying to Azure Container Instances..." -ForegroundColor Yellow

# Delete existing container group if it exists
az container delete --resource-group $resourceGroupName --name $containerGroupName --yes 2>$null

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
    Write-Host "Container deployed successfully!" -ForegroundColor Green
    
    # Get the FQDN
    Write-Host "Getting container FQDN..." -ForegroundColor Yellow
    $fqdn = az container show --resource-group $resourceGroupName --name $containerGroupName --query "ipAddress.fqdn" --output tsv
    Write-Host "Your app is available at: http://${fqdn}:8000" -ForegroundColor Cyan
    
    # Show container status
    Write-Host "Container status:" -ForegroundColor Yellow
    az container show --resource-group $resourceGroupName --name $containerGroupName --query "containers[0].instanceView.currentState" --output table
    
    # Show container logs
    Write-Host "Container logs (last 50 lines):" -ForegroundColor Yellow
    az container logs --resource-group $resourceGroupName --name $containerGroupName --tail 50
    
} else {
    Write-Host "Container deployment failed" -ForegroundColor Red
    Write-Host "Checking error details..." -ForegroundColor Yellow
    az container show --resource-group $resourceGroupName --name $containerGroupName
    exit 1
}

Write-Host "Deployment complete!" -ForegroundColor Green
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host "  - Container Registry: $acrLoginServer" -ForegroundColor White
Write-Host "  - Container Group: $containerGroupName" -ForegroundColor White
Write-Host "  - Public URL: http://${fqdn}:8000" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  - Test the application at the public URL" -ForegroundColor White
Write-Host "  - Monitor logs: az container logs --resource-group $resourceGroupName --name $containerGroupName --follow" -ForegroundColor White
Write-Host "  - Check status: az container show --resource-group $resourceGroupName --name $containerGroupName" -ForegroundColor White
