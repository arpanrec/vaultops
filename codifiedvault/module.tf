module "pki" {
  source = "./pki"

  providers = {
    vault = vault
  }
  codified_vault_addr      = local.codified_vault_addr
  codifiedvault_vault_fqdn = var.codifiedvault_vault_fqdn
}

module "policy" {
  source = "./policy"

  providers = {
    vault = vault
  }
}

module "auth" {
  source = "./auth"

  providers = {
    vault = vault
  }
  codified_vault_addr = local.codified_vault_addr
}

module "kv2" {
  source = "./kv2"

  providers = {
    vault = vault
  }
}
