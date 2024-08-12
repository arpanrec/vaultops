resource "vault_pki_secret_backend_role" "vault_client_certificate" {
  issuer_ref               = local.default_issuer_ref
  backend                  = vault_mount.pki.path
  name                     = "vault_client_certificate"
  ttl                      = (1 * 30 * 24 * 3600) # 1 months, (Months * Days * Hours * Seconds)
  max_ttl                  = (3 * 30 * 24 * 3600) # 3 months, (Months * Days * Hours * Seconds)
  allow_localhost          = true
  allowed_domains          = [var.codifiedvault_vault_fqdn]
  allow_subdomains         = true
  allow_bare_domains       = true
  allow_glob_domains       = true
  allow_any_name           = false
  allowed_domains_template = true
  server_flag              = false
  client_flag              = true
  code_signing_flag        = false
  email_protection_flag    = false
  key_type                 = "rsa"
  key_bits                 = 4096
  key_usage                = ["DigitalSignature", "KeyAgreement", "KeyEncipherment"]
  ext_key_usage            = ["ExtKeyUsageClientAuth"]
  allow_ip_sans            = true
  use_csr_common_name      = true
  use_csr_sans             = true
  require_cn               = true
}
