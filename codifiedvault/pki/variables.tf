variable "codifiedvault_vault_fqdn" {
  type    = any
  default = null
  validation {
    condition     = length(var.codifiedvault_vault_fqdn) > 1
    error_message = "Missing vault hostname"
  }
}

variable "codified_vault_addr" {
  type    = any
  default = null
  validation {
    condition     = length(var.codified_vault_addr) > 1
    error_message = "Missing vault Address"
  }
}
