data "vault_policy_document" "deny" {
  rule {
    path         = "*"
    capabilities = ["deny"]
    description  = "Allow all resources on vault for deny users"
  }
}
resource "vault_policy" "deny" {
  name   = "deny"
  policy = data.vault_policy_document.deny.hcl
}
