resource "google_compute_network" "private" {
  name                    = "umcp-private"
  auto_create_subnetworks = false
  depends_on              = [terraform_data.checkpoint_guard]
}

resource "google_compute_global_address" "private_service_access" {
  name          = "umcp-private-service-access"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.private.id
  depends_on    = [terraform_data.checkpoint_guard]
}

resource "google_service_networking_connection" "private_service_access" {
  network                 = google_compute_network.private.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_service_access.name]
  depends_on              = [terraform_data.checkpoint_guard]
}

resource "google_vpc_access_connector" "run" {
  name          = "umcp-run-private"
  region        = var.region
  network       = google_compute_network.private.name
  ip_cidr_range = "10.8.0.0/28"
  depends_on    = [terraform_data.checkpoint_guard]
}

resource "google_sql_database_instance" "primary" {
  name             = "umcp-postgres"
  database_version = "POSTGRES_16"
  region           = var.region
  depends_on       = [google_service_networking_connection.private_service_access]

  settings {
    tier              = "db-custom-1-3840"
    availability_type = "REGIONAL"
    disk_autoresize   = true

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.private.id
      ssl_mode        = "ENCRYPTED_ONLY"
    }

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7
      backup_retention_settings { retained_backups = 7 }
    }
  }

  deletion_protection = true
}

resource "google_sql_database" "application" {
  name     = "umcp"
  instance = google_sql_database_instance.primary.name
}
