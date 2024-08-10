data "vault_policy_document" "admin_read_only" {
  rule {
    path         = "*"
    capabilities = ["read", "list"]
    description  = "Allow to read resources on vault for super admin users"
  }
}
resource "vault_policy" "admin_read_only" {
  name   = "admin_read_only"
  policy = data.vault_policy_document.admin_read_only.hcl
}
