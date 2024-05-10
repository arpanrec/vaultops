variable "codifiedvault_vault_fqdn" {
  type      = string
  default   = null
  sensitive = false
  validation {
    condition     = length(var.codifiedvault_vault_fqdn) > 1
    error_message = "Missing FQDN"
  }
}

variable "codifiedvault_protocol" {
  type      = string
  default   = "https"
  sensitive = false
  validation {
    condition     = length(var.codifiedvault_protocol) > 1
    error_message = "Missing vault Protocol"
  }
}

variable "codifiedvault_vault_port" {
  type      = string
  default   = null
  sensitive = false
  validation {
    condition     = length(var.codifiedvault_vault_port) > 1
    error_message = "Missing vault Port"
  }
}

variable "codifiedvault_login_username" {
  type      = string
  default   = null
  sensitive = false
  validation {
    condition     = length(var.codifiedvault_login_username) > 1
    error_message = "Missing vault login username"
  }
}

variable "codifiedvault_login_userpass_mount_path" {
  type      = string
  default   = null
  sensitive = false
  validation {
    condition     = length(var.codifiedvault_login_userpass_mount_path) > 1
    error_message = "Missing vault login userpass mount point name"
  }
}

variable "codifiedvault_login_password" {
  type      = string
  default   = null
  sensitive = false
  validation {
    condition     = length(var.codifiedvault_login_password) > 1
    error_message = "Missing vault login password"
  }
}

variable "codifiedvault_vault_client_key_file" {
  type      = string
  default   = null
  sensitive = false
  validation {
    condition     = length(var.codifiedvault_vault_client_key_file) > 1
    error_message = "Missing vault mutual TLS auth private key file path"
  }
}

variable "codifiedvault_vault_client_cert_file" {
  type      = string
  default   = null
  sensitive = false
  validation {
    condition     = length(var.codifiedvault_vault_client_cert_file) > 1
    error_message = "Missing vault mutual TLS auth client certificate file path"
  }
}

variable "codifiedvault_vault_ca_file" {
  type      = string
  default   = null
  sensitive = false
  validation {
    condition     = length(var.codifiedvault_vault_ca_file) > 1
    error_message = "Missing vault mutual TLS auth private key file path"
  }
}
