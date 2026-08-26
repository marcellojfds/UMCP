resource "terraform_data" "checkpoint_guard" {
  input = {
    record      = var.checkpoint_record
    cp1         = var.cp1_approved
    cp3         = var.cp3_approved
    environment = var.environment
    image_digest = var.image_digest
    image_source_sha = var.image_source_sha
  }

  lifecycle {
    precondition {
      condition     = var.cp1_approved && var.cp3_approved && length(trimspace(var.checkpoint_record)) > 0
      error_message = "External infrastructure is blocked: CP-1 and CP-3 require an approved decision record."
    }
    precondition {
      condition     = length(trimspace(var.environment)) > 0
      error_message = "External infrastructure is blocked: environment must be explicitly approved."
    }
    precondition {
      condition     = can(regex("^.+@sha256:[0-9a-f]{64}$", var.image_digest)) && can(regex("^[0-9a-f]{40}$", var.image_source_sha))
      error_message = "External infrastructure is blocked: promotion requires an immutable image digest and its full source SHA."
    }
  }
}
