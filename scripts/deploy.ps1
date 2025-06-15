# Azure App Service Deployment Script for AI Language Learning App
# This script deploys the Streamlit application to Azure App Service

param(
    [string]$ResourceGroupName = "ai-language-app-rg",
    [string]$AppServiceName = "ailangapp-appservice"
)

Write-Host "🚀 Starting deployment to Azure App Service..." -ForegroundColor Green

# Check if Azure CLI is logged in
$account = az account show 2>$null
if (-not $account) {
    Write-Host "❌ Please log in to Azure CLI first: az login" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Azure CLI authenticated" -ForegroundColor Green

# Create deployment package (excluding unnecessary files)
Write-Host "📦 Creating deployment package..." -ForegroundColor Yellow

# Create temporary deployment directory
$deployDir = "deploy-temp"
if (Test-Path $deployDir) {
    Remove-Item $deployDir -Recurse -Force
}
New-Item -ItemType Directory -Path $deployDir

# Copy application files
Copy-Item "app" -Destination "$deployDir\app" -Recurse
Copy-Item "requirements.txt" -Destination "$deployDir\requirements.txt"
Copy-Item "startup.sh" -Destination "$deployDir\startup.sh" -ErrorAction SilentlyContinue

# Create .deployment file for App Service
@"
[config]
command = startup.sh
"@ | Out-File -FilePath "$deployDir\.deployment" -Encoding UTF8

Write-Host "✅ Deployment package created" -ForegroundColor Green

# Deploy to App Service using zip deployment
Write-Host "🚀 Deploying to Azure App Service: $AppServiceName..." -ForegroundColor Yellow

# Create zip file
$zipFile = "deployment.zip"
if (Test-Path $zipFile) {
    Remove-Item $zipFile
}

# Compress deployment directory
Compress-Archive -Path "$deployDir\*" -DestinationPath $zipFile

# Deploy zip to App Service
az webapp deployment source config-zip --resource-group $ResourceGroupName --name $AppServiceName --src $zipFile

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Deployment successful!" -ForegroundColor Green
    Write-Host "🌐 Your app is available at: https://$AppServiceName.azurewebsites.net" -ForegroundColor Cyan
    
    # Show app logs
    Write-Host "📊 Fetching application logs..." -ForegroundColor Yellow
    az webapp log tail --resource-group $ResourceGroupName --name $AppServiceName --provider application
} else {
    Write-Host "❌ Deployment failed. Check the logs above." -ForegroundColor Red
    exit 1
}

# Clean up
Remove-Item $deployDir -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $zipFile -ErrorAction SilentlyContinue

Write-Host "🎉 Deployment complete!" -ForegroundColor Green
