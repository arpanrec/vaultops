resource "vault_auth_backend" "approle" {
  type = "approle"
  path = "approle"
  tune {
    default_lease_ttl  = "768h"
    max_lease_ttl      = "768h"
    listing_visibility = "unauth"
    token_type         = "default-service"
  }
}

resource "vault_approle_auth_backend_role" "github-master-controller" {
  depends_on         = [vault_auth_backend.approle]
  backend            = vault_auth_backend.approle.path
  role_name          = "github-master-controller"
  token_policies     = ["default", "github-master-controller", "default_login"]
  secret_id_ttl      = 0
  role_id            = "github-master-controller"
  secret_id_num_uses = 0
}

resource "vault_approle_auth_backend_role" "gitlab-master-controller" {
  depends_on         = [vault_auth_backend.approle]
  backend            = vault_auth_backend.approle.path
  role_name          = "gitlab-master-controller"
  token_policies     = ["default", "gitlab-master-controller", "default_login"]
  secret_id_ttl      = 0
  role_id            = "gitlab-master-controller"
  secret_id_num_uses = 0
}

resource "vault_approle_auth_backend_role" "minio-kes" {
  depends_on         = [vault_auth_backend.approle]
  backend            = vault_auth_backend.approle.path
  role_name          = "minio-kes"
  token_policies     = ["default", "minio-kes", "default_login"]
  secret_id_ttl      = 0
  role_id            = "minio-kes"
  secret_id_num_uses = 0
  token_num_uses     = 0
}
