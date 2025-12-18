variable "project_id" {
  description = "Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "GCP region for resources (use us-central1, us-east1, or us-west1 for free tier)"
  type        = string
  default     = "us-central1"
}

variable "app_name" {
  description = "Application name used for resource naming"
  type        = string
  default     = "senda"
}

variable "staging_env_vars" {
  description = "Environment variables for staging environment"
  type        = map(string)
  default     = {}
  sensitive   = true
}

variable "production_env_vars" {
  description = "Environment variables for production environment"
  type        = map(string)
  default     = {}
  sensitive   = true
}

variable "initial_image" {
  description = "Initial Docker image to use for first deploy (leave empty to use Google's hello sample)"
  type        = string
  default     = ""
}
