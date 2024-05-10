data "vault_policy_document" "gitlab_master_controller" {
  rule {
    path         = "pki/issue/vault_client_certificate"
    capabilities = ["create", "update", "read"]
    description  = "Allow to create TLS client certificats for vault server"
  }
  rule {
    path         = "secret/data/external_services/gitlab"
    capabilities = ["read"]
    description  = "read gitlab credentials"
  }
  rule {
    path         = "secret/data/external_services/terraform_cloud"
    capabilities = ["read"]
    description  = "read terraform_cloud credentials"
  }
  rule {
    path         = "auth/approle/role/gitlab_master_controller/*"
    capabilities = ["create", "update", "read"]
  }
}

resource "vault_policy" "gitlab_master_controller" {
  name   = "gitlab_master_controller"
  policy = data.vault_policy_document.gitlab_master_controller.hcl
}
