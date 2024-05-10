data "vault_policy_document" "scm_cicd" {
  rule {
    path         = "pki/issue/client_certificate"
    capabilities = ["create", "update", "read"]
    description  = "Allow to create TLS client certificats"
  }
  rule {
    path         = "pki/issue/vault_client_certificate"
    capabilities = ["create", "update", "read"]
    description  = "Allow to create TLS client certificats for vault server"
  }
  rule {
    path         = "secret/*"
    capabilities = ["list", "read"]
    description  = "Allow to read secret"
  }
  rule {
    path         = "auth/approle/role/scm_cicd/secret-id-accessor/lookup"
    capabilities = ["update", "read"]
    description  = "Allow to check scm_cicd secret id accessor"
  }
  rule {
    path         = "auth/approle/role/scm_cicd/secret-id"
    capabilities = ["update", "read"]
    description  = "Allow to create scm_cicd secret id"
  }
}

resource "vault_policy" "scm_cicd" {
  name   = "scm_cicd"
  policy = data.vault_policy_document.scm_cicd.hcl
}
