resource "vault_pki_secret_backend_role" "client_certificate" {
  backend                  = vault_mount.pki.path
  name                     = "client_certificate"
  ttl                      = (0.25 * 365 * 24 * 3600) # Years * Days * Hours * Seconds
  max_ttl                  = (1 * 365 * 24 * 3600)    # Years * Days * Hours * Seconds
  allow_localhost          = true
  allowed_domains          = ["arpanrec.com", "*.arpanrec.com"]
  allow_subdomains         = true
  allow_bare_domains       = true
  allow_glob_domains       = true
  allow_any_name           = true
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
  issuer_ref               = local.default_issuer_ref
}
