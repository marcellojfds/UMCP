resource "google_storage_bucket" "terraform_state" {
  name                        = "${var.project_id}-umcp-tfstate"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  depends_on                  = [terraform_data.checkpoint_guard]

  versioning { enabled = true }
  retention_policy { retention_period = 2592000 }
}

resource "google_billing_budget" "monthly" {
  billing_account = var.billing_account_id
  display_name    = "umcp-${var.environment}-monthly"
  budget_filter { projects = ["projects/${var.project_id}"] }
  amount { specified_amount { currency_code = "USD" units = tostring(var.budget_amount_usd) } }
  threshold_rules { threshold_percent = 0.5 }
  threshold_rules { threshold_percent = 0.9 }
  threshold_rules { threshold_percent = 1.0 }
  depends_on = [terraform_data.checkpoint_guard]
}

resource "google_storage_bucket_iam_member" "deploy_state_writer" {
  bucket     = google_storage_bucket.terraform_state.name
  role       = "roles/storage.objectAdmin"
  member     = "serviceAccount:${google_service_account.workload[\"deploy\"].email}"
  depends_on = [terraform_data.checkpoint_guard]
}

resource "google_logging_project_sink" "security_audit" {
  name                   = "umcp-security-audit"
  destination            = "logging.googleapis.com/projects/${var.project_id}/locations/${var.region}/buckets/${google_logging_project_bucket_config.security.bucket_id}"
  filter                 = "severity>=WARNING"
  unique_writer_identity = true
  depends_on             = [terraform_data.checkpoint_guard]
}

resource "google_logging_project_bucket_config" "security" {
  project        = var.project_id
  location       = var.region
  retention_days = 30
  bucket_id      = "umcp-security"
  depends_on     = [terraform_data.checkpoint_guard]
}

resource "google_monitoring_alert_policy" "service_errors" {
  display_name = "umcp-api-error-rate"
  combiner     = "OR"
  conditions {
    display_name = "Cloud Run 5xx"
    condition_threshold {
      filter          = "metric.type=\"run.googleapis.com/request_count\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0
    }
  }
  depends_on = [terraform_data.checkpoint_guard]
}
