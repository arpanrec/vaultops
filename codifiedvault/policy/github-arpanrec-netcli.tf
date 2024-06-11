data "vault_policy_document" "github-arpanrec-netcli" {
  rule {
    path         = "vault-secrets/data/vault_secrets/github_details/github_bot"
    capabilities = ["read"]
    description  = "read github credentials"
  }
}

resource "vault_policy" "github-arpanrec-netcli" {
  name   = "github-arpanrec-netcli"
  policy = data.vault_policy_document.github-arpanrec-netcli.hcl
}
