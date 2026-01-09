terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# =============================================================================
# Enable Required APIs
# =============================================================================

resource "google_project_service" "run" {
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "artifactregistry" {
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "iam" {
  service            = "iam.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloudtasks" {
  service            = "cloudtasks.googleapis.com"
  disable_on_destroy = false
}

# =============================================================================
# Artifact Registry
# =============================================================================

resource "google_artifact_registry_repository" "senda" {
  location      = var.region
  repository_id = var.app_name
  description   = "Docker repository for ${var.app_name}"
  format        = "DOCKER"

  depends_on = [google_project_service.artifactregistry]
}

# =============================================================================
# Cloud Run Service - Staging
# =============================================================================

resource "google_cloud_run_v2_service" "staging" {
  name     = "${var.app_name}-staging"
  location = var.region

  template {
    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }

    containers {
      # Use sample image for initial deploy, GitHub Actions will update this
      image = var.initial_image != "" ? var.initial_image : "us-docker.pkg.dev/cloudrun/container/hello"

      ports {
        container_port = 8000
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }

      startup_probe {
        http_get {
          path = "/api/health-check"
          port = 8000
        }
        initial_delay_seconds = 5
        timeout_seconds       = 3
        period_seconds        = 10
        failure_threshold     = 3
      }

      liveness_probe {
        http_get {
          path = "/api/health-check"
          port = 8000
        }
        timeout_seconds   = 3
        period_seconds    = 30
        failure_threshold = 3
      }

      # Environment variables for staging
      dynamic "env" {
        for_each = var.staging_env_vars
        content {
          name  = env.key
          value = env.value
        }
      }

      # Common environment variable for app environment
      env {
        name  = "APP_ENV"
        value = "dev"
      }
    }

    max_instance_request_concurrency = 80
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [
    google_project_service.run,
    google_artifact_registry_repository.senda
  ]

  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
      client,
      client_version
    ]
  }
}

# =============================================================================
# Cloud Run Service - Production
# =============================================================================

resource "google_cloud_run_v2_service" "production" {
  name     = "${var.app_name}-production"
  location = var.region

  template {
    scaling {
      min_instance_count = 0
      max_instance_count = 10  # Limited by default GCP quota
    }

    containers {
      # Use sample image for initial deploy, GitHub Actions will update this
      image = var.initial_image != "" ? var.initial_image : "us-docker.pkg.dev/cloudrun/container/hello"

      ports {
        container_port = 8000
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "1Gi"
        }
        cpu_idle          = false
        startup_cpu_boost = true
      }

      startup_probe {
        http_get {
          path = "/api/health-check"
          port = 8000
        }
        initial_delay_seconds = 5
        timeout_seconds       = 3
        period_seconds        = 10
        failure_threshold     = 3
      }

      liveness_probe {
        http_get {
          path = "/api/health-check"
          port = 8000
        }
        timeout_seconds   = 3
        period_seconds    = 30
        failure_threshold = 3
      }

      # Environment variables for production
      dynamic "env" {
        for_each = var.production_env_vars
        content {
          name  = env.key
          value = env.value
        }
      }

      # Common environment variable for app environment
      env {
        name  = "APP_ENV"
        value = "prod"
      }
    }

    max_instance_request_concurrency = 80
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [
    google_project_service.run,
    google_artifact_registry_repository.senda
  ]

  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
      client,
      client_version
    ]
  }
}

# =============================================================================
# IAM - Allow Unauthenticated Access
# =============================================================================

resource "google_cloud_run_v2_service_iam_member" "staging_public" {
  project  = var.project_id
  location = google_cloud_run_v2_service.staging.location
  name     = google_cloud_run_v2_service.staging.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service_iam_member" "production_public" {
  project  = var.project_id
  location = google_cloud_run_v2_service.production.location
  name     = google_cloud_run_v2_service.production.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# =============================================================================
# Cloud Tasks - Job Processing Queues
# =============================================================================

# Service Account for Cloud Tasks to invoke Cloud Run
resource "google_service_account" "cloud_tasks_invoker" {
  account_id   = "${var.app_name}-tasks-invoker"
  display_name = "Cloud Tasks Invoker for ${var.app_name}"
  description  = "Service account used by Cloud Tasks to invoke Cloud Run services"

  depends_on = [google_project_service.iam]
}

# Grant Cloud Run Invoker role to the service account
resource "google_cloud_run_v2_service_iam_member" "staging_tasks_invoker" {
  project  = var.project_id
  location = google_cloud_run_v2_service.staging.location
  name     = google_cloud_run_v2_service.staging.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.cloud_tasks_invoker.email}"
}

resource "google_cloud_run_v2_service_iam_member" "production_tasks_invoker" {
  project  = var.project_id
  location = google_cloud_run_v2_service.production.location
  name     = google_cloud_run_v2_service.production.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.cloud_tasks_invoker.email}"
}

# Cloud Tasks Queue - Staging
resource "google_cloud_tasks_queue" "staging" {
  name     = "${var.app_name}-jobs-staging"
  location = var.region

  rate_limits {
    max_dispatches_per_second = 10
    max_concurrent_dispatches = 5
  }

  retry_config {
    max_attempts       = 3
    min_backoff        = "10s"
    max_backoff        = "300s"
    max_doublings      = 3
    max_retry_duration = "3600s"  # 1 hour max retry window
  }

  stackdriver_logging_config {
    sampling_ratio = 1.0  # Log all tasks for debugging in staging
  }

  depends_on = [google_project_service.cloudtasks]
}

# Cloud Tasks Queue - Production
resource "google_cloud_tasks_queue" "production" {
  name     = "${var.app_name}-jobs-production"
  location = var.region

  rate_limits {
    max_dispatches_per_second = 50
    max_concurrent_dispatches = 20
  }

  retry_config {
    max_attempts       = 5
    min_backoff        = "30s"
    max_backoff        = "600s"
    max_doublings      = 4
    max_retry_duration = "7200s"  # 2 hour max retry window
  }

  stackdriver_logging_config {
    sampling_ratio = 0.1  # Sample 10% of tasks in production
  }

  depends_on = [google_project_service.cloudtasks]
}
