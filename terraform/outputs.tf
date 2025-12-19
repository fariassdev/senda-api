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
