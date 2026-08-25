locals {
  service_accounts = {
    runtime     = "umcp-runtime"
    worker      = "umcp-worker"
    migration   = "umcp-migration"
    deploy      = "umcp-deploy"
    break_glass = "umcp-break-glass"
  }
}

resource "google_service_account" "workload" {
  for_each     = local.service_accounts
  account_id   = each.value
  display_name = "UMCP ${each.key} (H02 explicit identity)"
  depends_on   = [terraform_data.checkpoint_guard]
}

resource "google_project_iam_member" "runtime_sql_client" {
  project    = var.project_id
  role       = "roles/cloudsql.client"
  member     = "serviceAccount:${google_service_account.workload[\"runtime\"].email}"
  depends_on = [terraform_data.checkpoint_guard]
}

resource "google_project_iam_member" "worker_sql_client" {
  project    = var.project_id
  role       = "roles/cloudsql.client"
  member     = "serviceAccount:${google_service_account.workload[\"worker\"].email}"
  depends_on = [terraform_data.checkpoint_guard]
}

resource "google_project_iam_member" "migration_sql_client" {
  project    = var.project_id
  role       = "roles/cloudsql.client"
  member     = "serviceAccount:${google_service_account.workload[\"migration\"].email}"
  depends_on = [terraform_data.checkpoint_guard]
}

resource "google_project_iam_member" "deploy_run_developer" {
  project    = var.project_id
  role       = "roles/run.developer"
  member     = "serviceAccount:${google_service_account.workload[\"deploy\"].email}"
  depends_on = [terraform_data.checkpoint_guard]
}

resource "google_project_iam_member" "deploy_artifact_writer" {
  project    = var.project_id
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.workload[\"deploy\"].email}"
  depends_on = [terraform_data.checkpoint_guard]
}

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "umcp-github"
  display_name              = "UMCP GitHub OIDC"
  depends_on                = [terraform_data.checkpoint_guard]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-actions"
  display_name                       = "UMCP GitHub Actions restricted provider"
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
    "attribute.environment" = "assertion.environment"
  }
  attribute_condition = "assertion.repository == '${var.deploy_repository}' && assertion.ref == '${var.deploy_ref}' && assertion.environment == '${var.deploy_environment}'"
  oidc { issuer_uri = "https://token.actions.githubusercontent.com" }
  depends_on = [terraform_data.checkpoint_guard]
}

resource "google_service_account_iam_member" "deploy_wif_user" {
  service_account_id = google_service_account.workload["deploy"].name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.deploy_repository}"
  depends_on         = [terraform_data.checkpoint_guard]
}
