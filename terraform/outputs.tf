output "staging_url" {
  description = "URL of the staging Cloud Run service"
  value       = google_cloud_run_v2_service.staging.uri
}

output "production_url" {
  description = "URL of the production Cloud Run service"
  value       = google_cloud_run_v2_service.production.uri
}

output "artifact_registry" {
  description = "Artifact Registry repository URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${var.app_name}"
}

output "staging_service_name" {
  description = "Name of the staging Cloud Run service"
  value       = google_cloud_run_v2_service.staging.name
}

output "production_service_name" {
  description = "Name of the production Cloud Run service"
  value       = google_cloud_run_v2_service.production.name
}

# =============================================================================
# Cloud Tasks Outputs
# =============================================================================

output "staging_tasks_queue_name" {
  description = "Name of the staging Cloud Tasks queue"
  value       = google_cloud_tasks_queue.staging.name
}

output "production_tasks_queue_name" {
  description = "Name of the production Cloud Tasks queue"
  value       = google_cloud_tasks_queue.production.name
}

output "cloud_tasks_invoker_email" {
  description = "Email of the Cloud Tasks invoker service account"
  value       = google_service_account.cloud_tasks_invoker.email
}
