data "vault_policy_document" "minio-kes" {
  rule {
    path         = "pki/issue/vault_client_certificate"
    capabilities = ["create", "update", "read"]
    description  = "Allow to create TLS client certificats for vault server"
  }
  rule {
    path         = "minio-kes/data/*"
    capabilities = ["create", "read"]
    description  = "read write credentials"
  }
  rule {
    path         = "minio-kes/metadata/*"
    capabilities = ["list", "delete"]
    description  = "delete credentials"
  }
}

resource "vault_policy" "minio-kes" {
  name   = "minio-kes"
  policy = data.vault_policy_document.minio-kes.hcl
}
