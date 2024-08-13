from typing import Dict, Union

from pydantic import BaseModel, Field


class GitHubProdDetails(BaseModel):
    """
    Represents the GitHub production details.
    """

    GH_PROD_API_TOKEN: str = Field(description="The GitHub bot API token.")


class BotGpgDetails(BaseModel):
    """
    Attributes:
        BOT_GPG_PRIVATE_KEY: str: The GitHub Actions GPG private key.
        BOT_GPG_PASSPHRASE: str: The GitHub Actions GPG passphrase.
    """

    BOT_GPG_PRIVATE_KEY: str = Field(description="The GitHub Actions GPG private key.")
    BOT_GPG_PASSPHRASE: str = Field(description="The GitHub Actions GPG passphrase.")


class GitHubBotDetails(BaseModel):
    """
    Represents the GitHub bot details.
    """

    GH_BOT_API_TOKEN: str = Field(description="The GitHub production API token.")


class GithubDetails(BaseModel):
    """
    Represents the GitHub details.
    """

    github_bot: GitHubBotDetails = Field(description="The GitHub bot details.")
    github_prod: GitHubProdDetails = Field(description="The GitHub production details.")


class RootPkiDetails(BaseModel):
    """
    Represents the root PKI details.
    """

    root_ca_key_password: str = Field(description="The password for the root CA key.")
    root_ca_key_pem: str = Field(description="The PEM-encoded root CA key.")
    root_ca_cert_pem: str = Field(description="The PEM-encoded root CA certificate.")


class VaultAdminUserpassDetails(BaseModel):
    """
    Represents the Vault admin userpass details.
    """

    vault_admin_user: str = Field(description="The username of the Vault admin user.")
    vault_admin_password: str = Field(description="The password of the Vault admin user.")
    vault_admin_userpass_mount_path: str = Field(description="The mount path for the Vault admin userpass.")
    vault_admin_policy_name: str = Field(description="The name of the Vault admin policy.")
    vault_admin_client_cert_p12_passphrase: str = Field(
        description="The passphrase for the Vault admin client certificate."
    )


class VaultSecrets(BaseModel):
    """
    Represents the secrets required for interacting with HashiCorp Vault.
    """

    vault_ha_hostname: str = Field(description="The hostname of the Vault HA cluster.")
    vault_ha_port: int = Field(description="The port number of the Vault HA cluster.")
    github_details: GithubDetails = Field(description="The GitHub details.")
    root_pki_details: RootPkiDetails = Field(description="The root PKI details.")
    vault_admin_userpass_details: VaultAdminUserpassDetails = Field(description="The Vault admin userpass details.")
    external_services: Dict[str, Union[str, bool, int, Dict]] = Field(
        default={}, description="The external services required for the Vault HA cluster."
    )
    ansible_inventory: Dict[str, Union[str, bool, int, Dict]] = Field(
        default={}, description="The Ansible inventory details."
    )
    bot_gpg_key: BotGpgDetails = Field(description="The GitHub Actions GPG key details.")
