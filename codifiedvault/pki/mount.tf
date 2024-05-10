resource "vault_mount" "pki" {
  type                      = "pki"
  path                      = "pki"
  description               = "arpanrec vault intermediate certificate authority"
  default_lease_ttl_seconds = (20 * 12 * 30 * 24 * 3600) # 20 year,  (Years * Months * Days * Hours * Seconds)
  max_lease_ttl_seconds     = (20 * 12 * 30 * 24 * 3600) # 20 year,  (Years * Months * Days * Hours * Seconds)
}

resource "vault_pki_secret_backend_config_urls" "config_urls" {
  backend                 = vault_mount.pki.path
  issuing_certificates    = [format("%s%s", var.codified_vault_addr, "/v1/pki/ca")]
  crl_distribution_points = [format("%s%s", var.codified_vault_addr, "/v1/pki/crl")]
}

resource "vault_pki_secret_backend_crl_config" "crl_config" {
  backend     = vault_mount.pki.path
  disable     = false
  expiry      = "72h"
  ocsp_expiry = "12h"
}

resource "vault_pki_secret_backend_intermediate_cert_request" "pki_csr" {
  depends_on            = [vault_mount.pki]
  backend               = vault_mount.pki.path
  type                  = "internal"
  common_name           = "Vault - Certification Authority"
  format                = "pem_bundle"
  add_basic_constraints = true
  key_bits              = 4096
  key_type              = "rsa"
  key_name              = "pki"
}

data "vault_pki_secret_backend_issuers" "rootca" {
  backend = "root-ca"
}

resource "vault_pki_secret_backend_root_sign_intermediate" "root" {
  depends_on  = [vault_pki_secret_backend_intermediate_cert_request.pki_csr]
  backend     = data.vault_pki_secret_backend_issuers.rootca.backend
  csr         = vault_pki_secret_backend_intermediate_cert_request.pki_csr.csr
  common_name = vault_pki_secret_backend_intermediate_cert_request.pki_csr.common_name
  ttl         = (10 * 12 * 30 * 24 * 3600) # 10 year,  (Years * Months * Days * Hours * Seconds)
  issuer_ref  = keys(data.vault_pki_secret_backend_issuers.rootca.key_info)[0]
}

resource "vault_pki_secret_backend_intermediate_set_signed" "certificate" {
  depends_on  = [vault_pki_secret_backend_root_sign_intermediate.root]
  backend     = vault_mount.pki.path
  certificate = format("%s\n%s", vault_pki_secret_backend_root_sign_intermediate.root.certificate, vault_pki_secret_backend_root_sign_intermediate.root.issuing_ca)
}

locals {
  default_issuer_ref = (vault_pki_secret_backend_intermediate_set_signed.certificate.imported_issuers)[0]
}

resource "vault_pki_secret_backend_config_issuers" "config" {
  backend                       = vault_mount.pki.path
  default                       = local.default_issuer_ref
  default_follows_latest_issuer = true
}

resource "vault_pki_secret_backend_issuer" "set-name" {
  backend     = vault_mount.pki.path
  issuer_ref  = local.default_issuer_ref
  issuer_name = "root-ca"
}
