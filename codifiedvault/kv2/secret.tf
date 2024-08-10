resource "vault_mount" "secret" {
  path        = "secret"
  type        = "kv-v2"
  description = "secret"
  options = {
    version              = 2
    cas_required         = false
    max_versions         = 20
    delete_version_after = "0s"
  }
}
