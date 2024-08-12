resource "vault_mount" "kv" {
  path        = "kv"
  type        = "kv"
  description = "kv"
  options = {
    version = 1
  }
}
