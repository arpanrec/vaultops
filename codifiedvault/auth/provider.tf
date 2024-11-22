terraform {
  required_providers {
    vault = {
      source  = "hashicorp/vault"
      version = "4.5.0"
    }
  }
}


variable "codified_vault_addr" {
  type      = string
  default   = null
  sensitive = true
  validation {
    condition     = length(var.codified_vault_addr) > 1
    error_message = "Missing codified_vault_addr"
  }
}
