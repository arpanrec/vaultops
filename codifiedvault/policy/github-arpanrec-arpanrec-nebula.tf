data "vault_policy_document" "github-arpanrec-arpanrec-nebula" {
  rule {
    path         = "secret/data/vault_secrets/github_details/github_bot"
    capabilities = ["read"]
    description  = "read github credentials"
  }
  rule {
    path         = "secret/data/vault_secrets/external_services/ansible_galaxy"
    capabilities = ["read"]
    description  = "read ansible_galaxy credentials"
  }
  rule {
    path         = "auth/approle/role/github-arpanrec-arpanrec-nebula/*"
    capabilities = ["update"]
  }
}

resource "vault_policy" "github-arpanrec-arpanrec-nebula" {
  name   = "github-arpanrec-arpanrec-nebula"
  policy = data.vault_policy_document.github-arpanrec-arpanrec-nebula.hcl
}
