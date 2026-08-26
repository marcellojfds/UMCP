resource "google_cloud_run_v2_service" "api" {
  name     = "umcp-api"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"
  depends_on = [
    terraform_data.checkpoint_guard,
    google_vpc_access_connector.run,
    google_secret_manager_secret_iam_member.runtime_database_url,
  ]

  template {
    service_account = google_service_account.workload["runtime"].email
    timeout         = "30s"
    labels = {
      source-sha = var.image_source_sha
    }

    vpc_access {
      connector = google_vpc_access_connector.run.id
      egress    = "ALL_TRAFFIC"
    }

    containers {
      image = var.image_digest

      ports { container_port = 8080 }

      env { name = "PORT" value = "8080" }
      env {
        name = "OMP_DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.database_url.secret_id
            version = var.secret_version
          }
        }
      }
      env { name = "OMP_KMS_KEY_RESOURCE" value = google_kms_crypto_key.envelope.id }
    }
  }
}

# Deliberately no Cloud Run invoker binding is declared. The approved HTTPS
# edge is future H03/H07 work; direct public invocation is forbidden.
