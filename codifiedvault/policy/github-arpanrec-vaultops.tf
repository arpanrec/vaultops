data "vault_policy_document" "github-arpanrec-vaultops" {
  rule {
    path         = "secret/data/vault_secrets/github_details/github_bot"
    capabilities = ["read"]
    description  = "read github credentials"
  }
  rule {
    path         = "auth/approle/role/github-arpanrec-vaultops/*"
    capabilities = ["update"]
  }
}

resource "vault_policy" "github-arpanrec-vaultops" {
  name   = "github-arpanrec-vaultops"
  policy = data.vault_policy_document.github-arpanrec-vaultops.hcl
}
