data "vault_policy_document" "github-arpanrec-vaultops" {
  rule {
    path         = "vault-secrets/data/vault_secrets/github_details/github_bot"
    capabilities = ["read"]
    description  = "read github credentials"
  }
}

resource "vault_policy" "github-arpanrec-vaultops" {
  name   = "github-arpanrec-vaultops"
  policy = data.vault_policy_document.github-arpanrec-vaultops.hcl
}
