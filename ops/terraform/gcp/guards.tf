resource "terraform_data" "checkpoint_guard" {
  input = {
    record      = var.checkpoint_record
    cp1         = var.cp1_approved
    cp3         = var.cp3_approved
    environment = var.environment
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
  }
}
