data "vault_policy_document" "github-arpanrec-arpanrec-nebula" {
  rule {
    path         = "secret/data/external_services/github"
    capabilities = ["read"]
    description  = "read github credentials"
  }
  rule {
    path         = "secret/data/external_services/ansible_galaxy"
    capabilities = ["read"]
    description  = "read ansible_galaxy credentials"
  }
  rule {
    path         = "auth/approle/role/github-arpanrec-arpanrec-nebula/*"
    capabilities = ["create", "update", "read"]
  }
}

resource "vault_policy" "github-arpanrec-arpanrec-nebula" {
  name   = "github-arpanrec-arpanrec-nebula"
  policy = data.vault_policy_document.github-arpanrec-arpanrec-nebula.hcl
}
