terraform {
  backend "local" {
  }
  required_providers {
    vault = {
      source  = "hashicorp/vault"
      version = "4.5.0"
    }
  }
}

provider "vault" {
  address          = local.codified_vault_addr
  ca_cert_file     = var.codifiedvault_vault_ca_file
  skip_tls_verify  = false
  token_name       = "codified_vault"
  skip_child_token = false
  client_auth { # Changed from client_auth https://github.com/hashicorp/terraform-provider-vault/issues/2130
    cert_file = var.codifiedvault_vault_client_cert_file
    key_file  = var.codifiedvault_vault_client_key_file
  }
  auth_login {
    path = "auth/${var.codifiedvault_login_userpass_mount_path}/login/${var.codifiedvault_login_username}"
    parameters = {
      password = var.codifiedvault_login_password
    }
  }
}
