data "vault_policy_document" "github-arpanrec-arpanrec-vaultops" {
  rule {
    path         = "secret/data/external_services/github"
    capabilities = ["read"]
    description  = "read github credentials"
  }
  rule {
    path         = "auth/approle/role/github-arpanrec-arpanrec-vaultops/*"
    capabilities = ["create", "update", "read"]
  }
}

resource "vault_policy" "github-arpanrec-arpanrec-vaultops" {
  name   = "github-arpanrec-arpanrec-vaultops"
  policy = data.vault_policy_document.github-arpanrec-arpanrec-vaultops.hcl
}
