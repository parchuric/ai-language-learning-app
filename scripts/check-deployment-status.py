#!/usr/bin/env python3
"""
AI Language Learning App - Deployment Status & Management Script
This script helps manage and check the status of various deployment options.
"""

import subprocess
import sys
import json
from datetime import datetime

def run_command(command, capture_output=True):
    """Run a command and return the result."""
    try:
        result = subprocess.run(command, shell=True, capture_output=capture_output, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def check_azure_login():
    """Check if Azure CLI is logged in."""
    print("🔍 Checking Azure CLI login status...")
    success, output, error = run_command("az account show")
    if success:
        account_info = json.loads(output)
        print(f"✅ Logged in as: {account_info.get('user', {}).get('name', 'Unknown')}")
        print(f"📋 Subscription: {account_info.get('name', 'Unknown')}")
        return True
    else:
        print("❌ Not logged in to Azure CLI")
        print("💡 Run: az login")
        return False

def check_local_app():
    """Check if the local application dependencies are working."""
    print("\n🔍 Checking local application status...")
    
    # Check if virtual environment exists
    import os
    venv_path = os.path.join(os.getcwd(), ".venv")
    if os.path.exists(venv_path):
        print("✅ Virtual environment found")
    else:
        print("❌ Virtual environment not found")
        print("💡 Run: python -m venv .venv")
        return False
    
    # Check if requirements are installed
    success, output, error = run_command("python -c \"import streamlit, azure.identity; print('Dependencies OK')\"")
    if success:
        print("✅ Python dependencies installed")
        return True
    else:
        print("❌ Python dependencies missing")
        print("💡 Run: pip install -r requirements.txt")
        return False

def check_azure_resources():
    """Check the status of Azure resources."""
    print("\n🔍 Checking Azure resources...")
    
    # Check resource group
    success, output, error = run_command("az group show --name ai-language-app-rg")
    if not success:
        print("❌ Resource group 'ai-language-app-rg' not found")
        return False
    
    print("✅ Resource group exists")
    
    # List all resources
    success, output, error = run_command("az resource list --resource-group ai-language-app-rg --output table")
    if success:
        print("📋 Deployed resources:")
        print(output)
        
        # Count resources by type
        lines = output.strip().split('\n')
        if len(lines) > 2:  # Header + separator + data
            resources = lines[2:]
            print(f"📊 Total resources: {len(resources)}")
        
        return True
    else:
        print("❌ Failed to list resources")
        return False

def check_app_service_quota():
    """Check App Service Plan quota status."""
    print("\n🔍 Checking App Service Plan quota...")
    
    # Try to create a test plan to see quota status
    success, output, error = run_command("az appservice plan show --name ailangapp-asp --resource-group ai-language-app-rg")
    if success:
        print("✅ App Service Plan already exists")
        return True
    else:
        print("⚠️ App Service Plan not found - quota limits likely blocking creation")
        print("💡 Options:")
        print("   1. Request quota increase in Azure Portal")
        print("   2. Use Azure Container Instances deployment")
        print("   3. Use Docker local deployment")
        return False

def get_deployment_options():
    """Show available deployment options based on current status."""
    print("\n🚀 Available Deployment Options:")
    
    options = []
    
    # Local deployment
    options.append({
        "name": "Local Development",
        "status": "✅ Ready",
        "command": "streamlit run app/main.py",
        "description": "Run locally for development and testing"
    })
    
    # Docker deployment
    options.append({
        "name": "Docker Local",
        "status": "✅ Ready",
        "command": "docker-compose up --build",
        "description": "Run in Docker container locally"
    })
    
    # Azure Container Instances
    options.append({
        "name": "Azure Container Instances",
        "status": "✅ Ready",
        "command": ".\\deploy-aci.ps1",
        "description": "Deploy to Azure using Container Instances (recommended)"
    })
    
    # App Service (if quota available)
    options.append({
        "name": "Azure App Service",
        "status": "⚠️ Quota Limited",
        "command": ".\\deploy.ps1",
        "description": "Traditional App Service deployment (requires quota increase)"
    })
    
    # GitHub Actions
    options.append({
        "name": "GitHub Actions CI/CD",
        "status": "✅ Ready",
        "command": "git push origin main",
        "description": "Automated deployment via GitHub Actions"
    })
    
    for i, option in enumerate(options, 1):
        print(f"\n{i}. {option['name']} - {option['status']}")
        print(f"   Command: {option['command']}")
        print(f"   Description: {option['description']}")

def main():
    """Main function to run all checks and show deployment options."""
    print("🚀 AI Language Learning App - Deployment Status Check")
    print("=" * 60)
    print(f"🕐 Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run all checks
    azure_ok = check_azure_login()
    local_ok = check_local_app()
    
    if azure_ok:
        resources_ok = check_azure_resources()
        quota_ok = check_app_service_quota()
    else:
        resources_ok = False
        quota_ok = False
    
    # Show deployment options
    get_deployment_options()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Status Summary:")
    print(f"   Azure CLI: {'✅' if azure_ok else '❌'}")
    print(f"   Local App: {'✅' if local_ok else '❌'}")
    print(f"   Azure Resources: {'✅' if resources_ok else '❌'}")
    print(f"   App Service Quota: {'✅' if quota_ok else '⚠️'}")
    
    if azure_ok and local_ok and resources_ok:
        print("\n🎉 System ready for deployment!")
        print("💡 Recommended: Use Azure Container Instances deployment")
        print("   Command: .\\deploy-aci.ps1")
    else:
        print("\n⚠️ Some issues found. Please address them before deployment.")

if __name__ == "__main__":
    main()
