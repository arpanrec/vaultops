data "vault_policy_document" "gitlab-master-controller" {
  rule {
    path         = "pki/issue/vault_client_certificate"
    capabilities = ["create", "update", "read"]
    description  = "Allow to create TLS client certificats for vault server"
  }
  rule {
    path         = "vault-secrets/data/external_services/gitlab"
    capabilities = ["read"]
    description  = "read gitlab credentials"
  }
  rule {
    path         = "vault-secrets/data/external_services/terraform_cloud"
    capabilities = ["read"]
    description  = "read terraform_cloud credentials"
  }
  rule {
    path         = "auth/approle/role/gitlab-master-controller/*"
    capabilities = ["create", "update", "read"]
  }
}

resource "vault_policy" "gitlab-master-controller" {
  name   = "gitlab-master-controller"
  policy = data.vault_policy_document.gitlab-master-controller.hcl
}
