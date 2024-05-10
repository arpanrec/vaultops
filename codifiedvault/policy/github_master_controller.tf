data "vault_policy_document" "github_master_controller" {
  rule {
    path         = "pki/issue/vault_client_certificate"
    capabilities = ["create", "update", "read"]
    description  = "Allow to create TLS client certificats for vault server"
  }
  rule {
    path         = "secret/data/external_services/github"
    capabilities = ["read"]
    description  = "read github credentials"
  }
  rule {
    path         = "secret/data/external_services/terraform_cloud"
    capabilities = ["read"]
    description  = "read terraform_cloud credentials"
  }
  rule {
    path         = "auth/approle/role/github_master_controller/*"
    capabilities = ["create", "update", "read"]
  }
}

resource "vault_policy" "github_master_controller" {
  name   = "github_master_controller"
  policy = data.vault_policy_document.github_master_controller.hcl
}
