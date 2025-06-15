variable "resource_group_name" {
  description = "The name of the resource group where all resources will be created."
  type        = string
  default     = "ai-language-app-rg"
}

variable "location" {
  description = "The Azure region where resources will be created. Ensure services like Azure OpenAI (e.g., gpt-4o) are available here."
  type        = string
  default     = "East US" # Keep current deployed region
}

variable "project_prefix" {
  description = "A short prefix used for naming Azure resources to ensure uniqueness and grouping."
  type        = string
  default     = "ailangapp"
}

variable "openai_account_sku_name" {
  description = "The SKU name for the Azure OpenAI account."
  type        = string
  default     = "S0" # Standard tier.
}

variable "speech_service_sku_name" {
  description = "The SKU name for the Azure AI Speech service."
  type        = string
  default     = "S0" # Standard tier.
}

variable "content_safety_sku_name" {
  description = "The SKU name for the Azure AI Content Safety service."
  type        = string
  default     = "S0" # Standard tier.
}

variable "app_service_plan_sku_name" {
  description = "The SKU name for the App Service Plan (e.g., F1, B1, S1, P1V2)."
  type        = string
  default     = "B1" # Basic tier - more quota available than F1
}

variable "openai_deployment_name" {
  description = "The name for the Azure OpenAI model deployment (e.g., gpt-4o)."
  type        = string
  default     = "gpt-4o"
}

variable "openai_model_name" {
  description = "The model name for Azure OpenAI (e.g., gpt-4o)."
  type        = string
  default     = "gpt-4o"
}

variable "openai_model_version" {
  description = "The model version for Azure OpenAI (e.g., 2024-05-13 for gpt-4o)."
  type        = string
  default     = "2024-05-13" # Ensure this version is available in your region
}

variable "openai_deployment_scale_type" {
  description = "The scale type for the Azure OpenAI deployment (e.g., Standard, Manual)."
  type        = string
  default     = "Standard"
}
