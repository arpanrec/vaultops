resource "vault_mount" "minio-kes" {
  path        = "minio-kes"
  type        = "kv-v2"
  description = "minio-kes"
  options = {
    version              = 2
    cas_required         = false
    max_versions         = 20
    delete_version_after = "0s"
  }
}
