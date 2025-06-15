terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
  # It is recommended to configure authentication via Azure CLI, Service Principal, or Managed Identity.
  # For local development with Azure CLI: ensure you are logged in (`az login`).
}

resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
}

# Azure OpenAI Service
resource "azurerm_cognitive_account" "openai" {
  name                = "${var.project_prefix}-openai"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  kind                = "OpenAI"
  sku_name            = var.openai_account_sku_name

  tags = {
    environment = "development"
    project     = "AI Language Learning App"
  }
}

# Note on Azure OpenAI Model Deployment (e.g., gpt-4o):
# Terraform creates the Azure OpenAI *account*. Deploying specific models like 'gpt-4o'
# often requires an additional step after the account is provisioned.
# This can be done via the Azure Portal, Azure CLI (`az cognitiveservices account deployment create`),
# or using the `azurerm_cognitive_deployment` resource if you have confirmed model availability
# and have the necessary quota in your subscription and chosen region.
# Example for azurerm_cognitive_deployment (uncomment and adapt if ready):
resource "azurerm_cognitive_deployment" "gpt4o_deployment" {
  name                 = "gpt-4o" # Deployment name you choose
  cognitive_account_id = azurerm_cognitive_account.openai.id
  model {
    format  = "OpenAI"
    name    = "gpt-4o" # Model name as it appears in Azure
    version = "2024-05-13" # Model version for gpt-4o, verify availability
  }
  scale {
    type = "Standard" # Standard, Manual, etc. - For "Standard" no capacity is needed. For "Manual" capacity is required.
                     # Check Azure documentation for gpt-4o deployment scale settings.
  }
  depends_on = [
    azurerm_cognitive_account.openai
  ]
}

# Azure AI Speech Service
resource "azurerm_cognitive_account" "speech" {
  name                = "${var.project_prefix}-speech"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  kind                = "SpeechServices"
  sku_name            = var.speech_service_sku_name

  tags = {
    environment = "development"
    project     = "AI Language Learning App"
  }
}

# Store Speech Service Key in Key Vault
resource "azurerm_key_vault_secret" "speech_service_key" {
  name         = "${var.project_prefix}-speech-key" # Choose a descriptive name for the secret
  key_vault_id = azurerm_key_vault.main.id
  value        = azurerm_cognitive_account.speech.primary_access_key # Corrected attribute

  depends_on = [
    azurerm_cognitive_account.speech,
    azurerm_key_vault.main
  ]
}

# Azure AI Content Safety
resource "azurerm_cognitive_account" "content_safety" {
  name                = "${var.project_prefix}-contentsafety"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  kind                = "ContentSafety"
  sku_name            = var.content_safety_sku_name

  tags = {
    environment = "development"
    project     = "AI Language Learning App"
  }
}

# Azure Key Vault
resource "azurerm_key_vault" "main" {
  name                        = "${var.project_prefix}-kv"
  location                    = azurerm_resource_group.main.location
  resource_group_name         = azurerm_resource_group.main.name
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  sku_name                    = "standard"
  soft_delete_retention_days  = 7
  purge_protection_enabled    = false # Set to true for production

  # Enable access for the user/principal running Terraform to set initial secrets (if needed)
  # and for the App Service Managed Identity later.
  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id # Current user/SP running Terraform

    secret_permissions = [
      "Get", "List", "Set", "Delete"
    ]
  }

  tags = {
    environment = "development"
    project     = "AI Language Learning App"
  }
}

data "azurerm_client_config" "current" {}

# Azure Monitor - Log Analytics Workspace
resource "azurerm_log_analytics_workspace" "main" {
  name                = "${var.project_prefix}-loganalytics"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = {
    environment = "development"
    project     = "AI Language Learning App"
  }
}

# Azure Monitor - Application Insights
resource "azurerm_application_insights" "main" {
  name                = "${var.project_prefix}-appinsights"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web" # Suitable for Streamlit app

  tags = {
    environment = "development"
    project     = "AI Language Learning App"
  }
}

# Azure App Service Plan (Linux)
resource "azurerm_service_plan" "main" {
  name                = "${var.project_prefix}-asp"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  os_type             = "Linux"
  sku_name            = var.app_service_plan_sku_name # e.g., "B1", "S1", "P1V2"

  tags = {
    environment = "development"
    project     = "AI Language Learning App"
  }
}

# Azure App Service (Linux Web App for Python/Streamlit)
resource "azurerm_linux_web_app" "main" {
  name                = "${var.project_prefix}-appservice"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  service_plan_id     = azurerm_service_plan.main.id

  site_config {
    application_stack {
      python_version = "3.11" # Or your preferred Python version
    }
    # For Streamlit, you typically run it using `streamlit run app/main.py`
    # This can be configured via startup command or a custom Docker image.
    app_command_line = "python -m streamlit run app/main.py --server.port 8000 --server.address 0.0.0.0"
    http2_enabled = true # Enabling HTTP/2
    websockets_enabled = true # Streamlit uses WebSockets
  }

  # System-assigned Managed Identity for the App Service
  identity {
    type = "SystemAssigned"
  }

  # Store App Insights instrumentation key in App Settings
  app_settings = {
    "APPINSIGHTS_INSTRUMENTATIONKEY"        = azurerm_application_insights.main.instrumentation_key
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = azurerm_application_insights.main.connection_string
    # Add other environment variables your app will need, e.g., Key Vault URI, service endpoints
    "KEY_VAULT_URI"                         = azurerm_key_vault.main.vault_uri
    "AZURE_OPENAI_ENDPOINT"                 = azurerm_cognitive_account.openai.endpoint
    # "AZURE_SPEECH_ENDPOINT" removed as key will be fetched from KV, endpoint still useful
    "AZURE_SPEECH_ENDPOINT"                 = azurerm_cognitive_account.speech.endpoint 
    "AZURE_CONTENT_SAFETY_ENDPOINT"         = azurerm_cognitive_account.content_safety.endpoint
    # Name of the secret in Key Vault that holds the Speech API Key
    "AZURE_SPEECH_KEY_SECRET_NAME"          = azurerm_key_vault_secret.speech_service_key.name 
    "AZURE_OPENAI_DEPLOYMENT_NAME"          = azurerm_cognitive_deployment.gpt4o_deployment.name # Added for app consistency
  }

  tags = {
    environment = "development"
    project     = "AI Language Learning App"
  }
}

# Grant App Service's Managed Identity access to Key Vault
resource "azurerm_key_vault_access_policy" "app_service_policy" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_linux_web_app.main.identity[0].principal_id # Get principal ID of system-assigned identity

  secret_permissions = [
    "Get", "List"
  ]
}

# Grant App Service's Managed Identity access to Azure OpenAI
resource "azurerm_role_assignment" "app_service_openai_user" {
  scope                = azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services OpenAI User" # Or "Cognitive Services User"
  principal_id         = azurerm_linux_web_app.main.identity[0].principal_id
}

# Grant App Service's Managed Identity access to Azure Speech
resource "azurerm_role_assignment" "app_service_speech_user" {
  scope                = azurerm_cognitive_account.speech.id
  role_definition_name = "Cognitive Services User"
  principal_id         = azurerm_linux_web_app.main.identity[0].principal_id
}

# Grant App Service's Managed Identity access to Azure Content Safety
resource "azurerm_role_assignment" "app_service_contentsafety_user" {
  scope                = azurerm_cognitive_account.content_safety.id
  role_definition_name = "Cognitive Services User" # Or a more specific Content Safety role if available
  principal_id         = azurerm_linux_web_app.main.identity[0].principal_id
}

# Note on Managed Identities:
# The above configurations for azurerm_role_assignment and azurerm_key_vault_access_policy
# set up the App Service's system-assigned managed identity to access other Azure services.
# This is a secure way to manage credentials. Your application code will use Azure Identity SDK
# with DefaultAzureCredential to authenticate to these services.
