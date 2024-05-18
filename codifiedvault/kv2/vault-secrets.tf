resource "vault_mount" "vault-secrets" {
  path        = "vault-secrets"
  type        = "kv-v2"
  description = "vault-secrets"
  options = {
    version              = 2
    cas_required         = false
    max_versions         = 20
    delete_version_after = "0s"
  }
}
