output "resource_group_name" {
  description = "The name of the created resource group."
  value       = azurerm_resource_group.main.name
}

output "location" {
  description = "The Azure region where resources are deployed."
  value       = azurerm_resource_group.main.location
}

output "key_vault_name" {
  description = "The name of the created Azure Key Vault."
  value       = azurerm_key_vault.main.name
}

output "key_vault_uri" {
  description = "The URI of the created Azure Key Vault."
  value       = azurerm_key_vault.main.vault_uri
}

output "app_insights_instrumentation_key" {
  description = "The instrumentation key for Application Insights."
  value       = azurerm_application_insights.main.instrumentation_key
  sensitive   = true
}

output "app_insights_connection_string" {
  description = "The connection string for Application Insights."
  value       = azurerm_application_insights.main.connection_string
  sensitive   = true
}

output "app_service_name" {
  description = "The name of the created App Service."
  value       = azurerm_linux_web_app.main.name
}

output "app_service_default_hostname" {
  description = "The default hostname of the App Service."
  value       = azurerm_linux_web_app.main.default_hostname
}

output "openai_account_name" {
  description = "The name of the Azure OpenAI account."
  value       = azurerm_cognitive_account.openai.name
}

output "openai_account_endpoint" {
  description = "The endpoint of the Azure OpenAI account."
  value       = azurerm_cognitive_account.openai.endpoint
}

output "speech_service_name" {
  description = "The name of the Azure AI Speech service."
  value       = azurerm_cognitive_account.speech.name
}

output "speech_service_endpoint" {
  description = "The endpoint of the Azure AI Speech service."
  value       = azurerm_cognitive_account.speech.endpoint
}

output "content_safety_name" {
  description = "The name of the Azure AI Content Safety service."
  value       = azurerm_cognitive_account.content_safety.name
}

output "content_safety_endpoint" {
  description = "The endpoint of the Azure AI Content Safety service."
  value       = azurerm_cognitive_account.content_safety.endpoint
}
