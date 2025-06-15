#!/usr/bin/env python3
"""
Azure App Service Deployment Script for AI Language Learning App
This script handles the deployment of the Streamlit application to Azure App Service.
"""

import os
import sys
import subprocess
import zipfile
import tempfile
import shutil
from pathlib import Path

# Configuration
RESOURCE_GROUP = "ai-language-app-rg"
APP_SERVICE_NAME = "ailangapp-appservice"

# Files to include in deployment
DEPLOYMENT_FILES = [
    "app/",
    "requirements.txt",
    "startup.sh",
]

# Files to exclude
EXCLUDE_PATTERNS = [
    ".env",
    ".venv/",
    "terraform/",
    "__pycache__/",
    "*.pyc",
    ".git/",
    ".github/",
    "deploy.ps1",
    "deploy.py"
]

def run_command(cmd, shell=True):
    """Run a shell command and return the result."""
    print(f"🔧 Running: {cmd}")
    try:
        result = subprocess.run(cmd, shell=shell, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {e}")
        print(f"Error output: {e.stderr}")
        return None

def check_azure_cli():
    """Check if Azure CLI is installed and user is logged in."""
    print("🔍 Checking Azure CLI...")
    
    # Check if az command exists
    if run_command("az --version") is None:
        print("❌ Azure CLI not found. Please install Azure CLI.")
        return False
    
    # Check if user is logged in
    if run_command("az account show") is None:
        print("❌ Please log in to Azure CLI: az login")
        return False
    
    print("✅ Azure CLI is ready")
    return True

def create_deployment_package():
    """Create a deployment package with only necessary files."""
    print("📦 Creating deployment package...")
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        deploy_dir = Path(temp_dir) / "deploy"
        deploy_dir.mkdir()
        
        # Copy application files
        for item in DEPLOYMENT_FILES:
            src = Path(item)
            if src.exists():
                if src.is_dir():
                    shutil.copytree(src, deploy_dir / src.name)
                else:
                    shutil.copy2(src, deploy_dir / src.name)
                print(f"📁 Copied: {item}")
        
        # Create .deployment file for App Service
        deployment_config = """[config]
command = startup.sh
"""
        (deploy_dir / ".deployment").write_text(deployment_config)
        
        # Create zip file
        zip_path = Path("deployment.zip")
        if zip_path.exists():
            zip_path.unlink()
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(deploy_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(deploy_dir)
                    zipf.write(file_path, arcname)
        
        print(f"✅ Deployment package created: {zip_path}")
        return zip_path

def deploy_to_azure(zip_path):
    """Deploy the zip package to Azure App Service."""
    print(f"🚀 Deploying to Azure App Service: {APP_SERVICE_NAME}...")
    
    cmd = f"az webapp deployment source config-zip --resource-group {RESOURCE_GROUP} --name {APP_SERVICE_NAME} --src {zip_path}"
    
    if run_command(cmd):
        print("✅ Deployment successful!")
        print(f"🌐 Your app is available at: https://{APP_SERVICE_NAME}.azurewebsites.net")
        return True
    else:
        print("❌ Deployment failed")
        return False

def show_app_logs():
    """Show application logs from Azure App Service."""
    print("📊 Fetching recent application logs...")
    
    cmd = f"az webapp log download --resource-group {RESOURCE_GROUP} --name {APP_SERVICE_NAME} --log-file app-logs.zip"
    run_command(cmd)
    
    # Also try to get live logs
    print("📊 Live log stream (press Ctrl+C to exit):")
    cmd = f"az webapp log tail --resource-group {RESOURCE_GROUP} --name {APP_SERVICE_NAME}"
    subprocess.run(cmd, shell=True)

def main():
    """Main deployment function."""
    print("🚀 AI Language Learning App - Azure Deployment")
    print("=" * 50)
    
    # Check prerequisites
    if not check_azure_cli():
        sys.exit(1)
    
    try:
        # Create deployment package
        zip_path = create_deployment_package()
        
        # Deploy to Azure
        if deploy_to_azure(zip_path):
            print("\n🎉 Deployment completed successfully!")
            
            # Clean up
            if zip_path.exists():
                zip_path.unlink()
            
            # Optionally show logs
            response = input("\n📊 Would you like to view application logs? (y/N): ")
            if response.lower() in ['y', 'yes']:
                show_app_logs()
                
        else:
            print("\n❌ Deployment failed. Please check the errors above.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
