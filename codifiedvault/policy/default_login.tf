data "vault_policy_document" "default_login" {
  rule {
    path         = "auth/token/lookup-self"
    capabilities = ["read"]
    description  = "Allow tokens to look up their own properties"
  }
  rule {
    path         = "auth/token/renew-self"
    capabilities = ["update"]
    description  = "Allow tokens to renew themselves"
  }
  rule {
    path         = "auth/token/revoke-self"
    capabilities = ["update"]
    description  = "Allow tokens to revoke themselves"
  }
  rule {
    path         = "auth/token/create"
    capabilities = ["update"]
    description  = "create limited child token"
  }
  rule {
    path         = "config/data/*"
    capabilities = ["read", "list"]
    description  = "Cloud Config Server"
  }
}

resource "vault_policy" "default_login" {
  name   = "default_login"
  policy = data.vault_policy_document.default_login.hcl
}
