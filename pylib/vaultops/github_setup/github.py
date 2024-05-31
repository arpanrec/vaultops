import base64
import json
import logging
from typing import Any, Dict, List, Optional, Union

import hvac  # type: ignore
from github import Auth, Github
from github.AuthenticatedUser import AuthenticatedUser
from github.NamedUser import NamedUser
from hvac.exceptions import InvalidPath  # type: ignore

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
    github_prod_vault_secret: Dict[str, Any]
    github_bot_user: Optional[Union[NamedUser, AuthenticatedUser]] = _get_bot_account(client)
    try:
        github_prod_vault_secret = client.secrets.kv.v2.read_secret_version(
            path="vault_secrets/github_details/github_prod",
            mount_point="vault-secrets",
        )
    except InvalidPath as e:
        LOGGER.info("github_prod secret not found, Skipping GitHub setup, error: %s", e)
        return
    except Exception as e:  # pylint: disable=broad-except
        raise ValueError("Error reading secret vault_secrets/github_details/github_prod") from e

    github_prod_secret_dict = github_prod_vault_secret["data"]["data"]

    if "GH_PROD_API_TOKEN" not in github_prod_secret_dict:
        LOGGER.warning("GH_PROD_API_TOKEN not found in GitHub secret, Skipping GitHub setup")
        return

    LOGGER.debug("GitHub secret version response: %s", github_prod_secret_dict)
    auth = Auth.Token(github_prod_secret_dict["GH_PROD_API_TOKEN"])
    g = Github(auth=auth)
    user = g.get_user()
    LOGGER.info("GitHub user: %s", user.login)
    all_repos_with_access = user.get_repos()
    for repo in all_repos_with_access:
        if user.login == repo.owner.login and not repo.private:
            vault_access_secrets: Optional[Dict[str, str]] = __get_access_secrets(
                vault_ha_client, user.login, repo.name
            )
            if vault_access_secrets:
                __set_up_github_access_credential(
                    access_secrets=vault_access_secrets,
                    repository_full_name=repo.full_name,
                    pat=github_prod_secret_dict["GH_PROD_API_TOKEN"],
                )
                if github_bot_user:
                    LOGGER.info("Adding bot as collaborator to %s repository", repo.full_name)
                    repo.add_to_collaborators(github_bot_user.login, permission="admin")


def __get_access_secrets(vault_ha_client: VaultHaClient, github_user: str, repo_name: str) -> Optional[Dict[str, str]]:
    """
    This function will get the access secrets.
    Args:
        vault_ha_client (VaultHaClient): The vault client.
    Returns:
        dict: The access secrets.
    """
    client = vault_ha_client.hvac_client()
    list_roles = client.list("auth/approle/role")["data"].get("keys", [])
    repo_name_sanitized = repo_name.replace(".", "-")
    approle_name = f"github-{github_user}-{repo_name_sanitized}"

    if approle_name not in list_roles:
        LOGGER.info("No AppRole found for GitHub user: %s, repo: %s", github_user, repo_name)
        return None

    LOGGER.info("AppRole found for GitHub user: %s, repo: %s", github_user, repo_name)
    LOGGER.info("Adding vault access to %s repository", repo_name)

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


def __set_up_github_access_credential(access_secrets: Dict[str, str], repository_full_name: str, pat: str):
    """
    This function will set up the GitHub repository.
    """
    for key, value in access_secrets.items():
        LOGGER.debug("Setting up GitHub repository: %s, key: %s", repository_full_name, key)
        github_variable(pat=pat, unencrypted_value=value, repository=repository_full_name, name=key)


def _get_bot_account(client: hvac.Client) -> Optional[Union[NamedUser, AuthenticatedUser]]:
    try:
        secret_version_response = client.secrets.kv.v2.read_secret_version(
            path="vault_secrets/github_details/github_bot",
            mount_point="vault-secrets",
        )

        if "GH_BOT_API_TOKEN" not in secret_version_response["data"]["data"]:
            LOGGER.warning("GH_BOT_API_TOKEN not found in GitHub bot secret, Skipping GitHub setup")
            return None

        auth = Auth.Token(secret_version_response["data"]["data"]["GH_BOT_API_TOKEN"])
        g = Github(auth=auth)
        return g.get_user()

    except InvalidPath as e:
        LOGGER.info("github_bot secret not found, error: %s", e)
        return None
    except Exception as e:  # pylint: disable=broad-except
        raise ValueError("Error reading secret vault_secrets/github_details/github_bot") from e
