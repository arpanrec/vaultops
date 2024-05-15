import base64
import json
import logging
from typing import Dict, List

from github import Auth, Github

from ..models.ha_client import VaultHaClient
from ..utils.github_variable import github_variable

LOGGER = logging.getLogger(__name__)


def add_vault_access_to_github(vault_ha_client: VaultHaClient):
    """
    This function will add the vault access to the GitHub repository.
    Args:
        vault_ha_client (VaultHaClient): The vault client.
    """
    LOGGER.info("Adding vault access to GitHub user repositories")

    client = vault_ha_client.hvac_client()
    secret_version_response = client.secrets.kv.v2.read_secret_version(
        path="external_services/github",
    )
    github_secret_version_response = secret_version_response["data"]["data"]
    LOGGER.debug("GitHub secret version response: %s", github_secret_version_response)
    auth = Auth.Token(github_secret_version_response["GH_PROD_API_TOKEN"])
    g = Github(auth=auth)
    user = g.get_user()
    LOGGER.info("GitHub user: %s", user.login)
    all_repos_with_access = user.get_repos()
    for repo in all_repos_with_access:
        if user.login == repo.owner.login and not repo.private:
            LOGGER.info("Adding vault access to %s repository", repo.full_name)
            vault_access_secrets: Dict[str, str] = __get_access_secrets(vault_ha_client, user.login, repo.name)
            __set_up_github_access_credential(
                access_secrets=vault_access_secrets,
                repo=repo.full_name,
                pat=github_secret_version_response["GH_PROD_API_TOKEN"],
            )


def __get_access_secrets(vault_ha_client: VaultHaClient, github_user: str, repo_name: str) -> Dict[str, str]:
    """
    This function will get the access secrets.
    Args:
        vault_ha_client (VaultHaClient): The vault client.
    Returns:
        dict: The access secrets.
    """
    client = vault_ha_client.hvac_client()
    list_roles = client.list("auth/approle/role")["data"].get("keys", [])
    approle_name = "github-master-controller"

    repo_name_sanitized = repo_name.replace(".", "-")

    if f"github-{github_user}-{repo_name_sanitized}" in list_roles:
        approle_name = f"github-{github_user}-{repo_name_sanitized}"

    LOGGER.info("Approle name: %s, for GitHub user: %s, repo: %s", approle_name, github_user, repo_name)

    role_id = client.auth.approle.read_role_id(role_name=approle_name, mount_point="approle")["data"]["role_id"]

    secret_id = client.auth.approle.generate_secret_id(role_name=approle_name, mount_point="approle")["data"][
        "secret_id"
    ]

    generate_certificate_response = client.secrets.pki.generate_certificate(
        name="vault_client_certificate",
        mount_point="pki",
        common_name=f"{vault_ha_client.vault_ha_hostname}",
    )

    issues_ca_list: List[str] = generate_certificate_response["data"]["ca_chain"]
    cert_full_chain: List[str] = [generate_certificate_response["data"]["certificate"]] + issues_ca_list
    vault_access_secrets = {
        "VAULT_ADDR": f"https://{vault_ha_client.vault_ha_hostname}:{vault_ha_client.vault_ha_port}",
        "VAULT_APPROLE_ROLE_ID": role_id,
        "VAULT_APPROLE_SECRET_ID": secret_id,
        "VAULT_CLIENT_PRIVATE_KEY_CONTENT_BASE64": base64.b64encode(
            generate_certificate_response["data"]["private_key"].encode("utf-8")
        ).decode("utf-8"),
        "ROOT_CA_CERTIFICATE_CONTENT_BASE64": base64.b64encode(("\n".join(cert_full_chain)).encode("utf-8")).decode(
            "utf-8"
        ),
        "VAULT_CLIENT_CERTIFICATE_CONTENT_BASE64": base64.b64encode(
            ("\n".join(cert_full_chain)).encode("utf-8")
        ).decode("utf-8"),
    }
    LOGGER.debug("Vault access secrets: %s", json.dumps(vault_access_secrets, indent=4))
    return vault_access_secrets


def __set_up_github_access_credential(access_secrets: Dict[str, str], repo: str, pat: str):
    """
    This function will set up the GitHub repository.
    """
    for key, value in access_secrets.items():
        LOGGER.debug("Setting up GitHub repository: %s, key: %s", repo, key)
        github_variable(pat=pat, unencrypted_value=value, repository=repo, name=key)
