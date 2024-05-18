data "vault_policy_document" "github-master-controller" {
  rule {
    path         = "pki/issue/vault_client_certificate"
    capabilities = ["create", "update", "read"]
    description  = "Allow to create TLS client certificats for vault server"
  }
  rule {
    path         = "vault-secrets/data/external_services/github"
    capabilities = ["read"]
    description  = "read github credentials"
  }
  rule {
    path         = "vault-secrets/data/external_services/terraform_cloud"
    capabilities = ["read"]
    description  = "read terraform_cloud credentials"
  }
  rule {
    path         = "vault-secrets/data/external_services/pulumi"
    capabilities = ["read"]
    description  = "read pulumi credentials"
  }
  rule {
    path         = "vault-secrets/data/external_services/ansible_galaxy"
    capabilities = ["read"]
    description  = "read ansible_galaxy credentials"
  }
  rule {
    path         = "auth/approle/role/github-master-controller/*"
    capabilities = ["create", "update", "read"]
  }
}

resource "vault_policy" "github-master-controller" {
  name   = "github-master-controller"
  policy = data.vault_policy_document.github-master-controller.hcl
}
