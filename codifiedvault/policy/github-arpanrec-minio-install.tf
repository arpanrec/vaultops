data "vault_policy_document" "github-arpanrec-minio-install" {
  rule {
    path         = "vault-secrets/data/vault_secrets/github_details/github_bot"
    capabilities = ["read"]
    description  = "read github credentials"
  }
}

resource "vault_policy" "github-arpanrec-minio-install" {
  name   = "github-arpanrec-minio-install"
  policy = data.vault_policy_document.github-arpanrec-minio-install.hcl
}
