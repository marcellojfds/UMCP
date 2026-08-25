resource "google_kms_key_ring" "umcp" {
  name       = "umcp"
  location   = var.region
  depends_on = [terraform_data.checkpoint_guard]
}

resource "google_kms_crypto_key" "envelope" {
  name            = "umcp-envelope"
  key_ring        = google_kms_key_ring.umcp.id
  rotation_period = "2592000s"
  lifecycle { prevent_destroy = true }
}

resource "google_secret_manager_secret" "database_url" {
  secret_id = "umcp-database-url"
  replication {
    user_managed {
      replicas { location = var.region }
    }
  }
  depends_on = [terraform_data.checkpoint_guard]
}

resource "google_secret_manager_secret_iam_member" "runtime_database_url" {
  secret_id  = google_secret_manager_secret.database_url.id
  role       = "roles/secretmanager.secretAccessor"
  member     = "serviceAccount:${google_service_account.workload[\"runtime\"].email}"
  depends_on = [terraform_data.checkpoint_guard]
}

resource "google_kms_crypto_key_iam_member" "runtime_envelope" {
  crypto_key_id = google_kms_crypto_key.envelope.id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member        = "serviceAccount:${google_service_account.workload[\"runtime\"].email}"
  depends_on    = [terraform_data.checkpoint_guard]
}

resource "google_kms_crypto_key_iam_member" "worker_envelope" {
  crypto_key_id = google_kms_crypto_key.envelope.id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member        = "serviceAccount:${google_service_account.workload[\"worker\"].email}"
  depends_on    = [terraform_data.checkpoint_guard]
}
