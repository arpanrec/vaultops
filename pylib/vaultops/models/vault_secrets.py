from typing import Dict, Union

from pydantic import BaseModel, Field
from ..models.github_secrets import GitHubDetails


class VaultSecrets(BaseModel):
    """
    Represents the secrets required for interacting with HashiCorp Vault.
    """

    root_ca_key_password: str = Field(description="The password for the root CA key.")
    root_ca_key_pem: str = Field(description="The PEM-encoded root CA key.")
    root_ca_cert_pem: str = Field(description="The PEM-encoded root CA certificate.")
    vault_ha_hostname: str = Field(description="The hostname of the Vault HA cluster.")
    vault_ha_port: int = Field(description="The port number of the Vault HA cluster.")
    vault_admin_user: str = Field(description="The username of the Vault admin user.")
    vault_admin_password: str = Field(description="The password of the Vault admin user.")
    vault_admin_userpass_mount_path: str = Field(description="The mount path for the Vault admin userpass.")
    vault_admin_policy_name: str = Field(description="The name of the Vault admin policy.")
    vault_admin_client_cert_p12_passphrase: str = Field(
        description="The passphrase for the Vault admin client certificate."
    )
    external_services: Dict[str, Union[str, bool, int, Dict]] = Field(
        default={}, description="The external services required for the Vault HA cluster."
    )
    GH_BOT_API_TOKEN: str = Field(description="The GitHub bot API token.")
    GH_BOT_GPG_PRIVATE_KEY: str = Field(description="The GitHub Actions GPG private key.")
    GH_BOT_GPG_PASSPHRASE: str = Field(description="The GitHub Actions GPG passphrase.")
    GH_PROD_API_TOKEN: str = Field(description="The GitHub production API token.")
