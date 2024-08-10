data "vault_policy_document" "minio-kes" {
  rule {
    path         = "kv/minio/kes/kms/*"
    capabilities = ["create", "read", "delete", "update", "list"]
    description  = "All operations on the minio/kes/kms path"
  }
  rule {
    path         = "secret/data/minio/kes/kms/*"
    capabilities = ["create", "read"]
    description  = "read and write credentials"
  }
  rule {
    path         = "secret/metadata/minio/kes/kms/*"
    capabilities = ["list", "delete"]
    description  = "delete and list credentials"
  }
}

resource "vault_policy" "minio-kes" {
  name   = "minio-kes"
  policy = data.vault_policy_document.minio-kes.hcl
}
