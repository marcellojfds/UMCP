terraform {
  required_version = ">= 1.7.0, < 2.0.0"

  # The bucket/prefix are intentionally supplied only by an approved, external
  # bootstrap procedure. No local backend configuration names a project/bucket.
  backend "gcs" {}

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
