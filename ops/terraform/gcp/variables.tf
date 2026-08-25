variable "project_id" {
  description = "CP-1-approved GCP project ID; deliberately has no default."
  type        = string
  nullable    = false
}

variable "region" {
  description = "Primary data-plane region frozen by ADR 0016."
  type        = string
  default     = "southamerica-east1"

  validation {
    condition     = var.region == "southamerica-east1"
    error_message = "H02 permits only southamerica-east1 until a new ADR is approved."
  }
}

variable "environment" {
  type        = string
  description = "CP-1-approved environment; H02 supplies no deployment default."
}

variable "checkpoint_record" {
  type        = string
  description = "Approved CP-1 and CP-3 decision-record identifier; never a credential."
  default     = ""
}

variable "cp1_approved" {
  type        = bool
  description = "Must be true only after the human CP-1 decision is recorded."
  default     = false
}

variable "cp3_approved" {
  type        = bool
  description = "Must be true only after the human CP-3 decision is recorded."
  default     = false
}

variable "image_digest" {
  type        = string
  description = "Immutable Artifact Registry image reference, including @sha256 digest."

  validation {
    condition     = can(regex("^.+@sha256:[0-9a-f]{64}$", var.image_digest))
    error_message = "image_digest must be an immutable image reference with a sha256 digest."
  }
}

variable "deploy_repository" {
  type        = string
  description = "Exact GitHub owner/repository allowed to exchange OIDC tokens."
}

variable "deploy_ref" {
  type        = string
  description = "Exact protected Git ref allowed to deploy."
}

variable "deploy_environment" {
  type        = string
  description = "Exact GitHub Environment required for WIF exchange."
}

variable "secret_version" {
  type        = string
  description = "Approved immutable Secret Manager version; latest is forbidden."

  validation {
    condition     = can(regex("^[1-9][0-9]*$", var.secret_version))
    error_message = "secret_version must be a positive immutable version number."
  }
}

variable "billing_account_id" {
  type        = string
  description = "CP-1-approved billing account ID; deliberately has no default."
  sensitive   = true
}

variable "budget_amount_usd" {
  type        = number
  description = "CP-1-approved monthly budget in USD; deliberately has no default."
  nullable    = false

  validation {
    condition     = var.budget_amount_usd > 0
    error_message = "budget_amount_usd must be a positive CP-1-approved limit."
  }
}
