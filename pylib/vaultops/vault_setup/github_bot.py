import logging
import os
import tempfile
from typing import Tuple

import gnupg  # type: ignore
import requests
from hvac.exceptions import InvalidPath  # type: ignore

from ..models.ha_client import VaultHaClient

LOGGER = logging.getLogger(__name__)


def add_gpg_to_bot_github(vault_ha_client: VaultHaClient):
    """
    This function will GPG public key to the GitHub account.
    Args:
        vault_ha_client (VaultHaClient): The vault client.
    """

    client = vault_ha_client.hvac_client()
    try:
        secret_version_response = client.secrets.kv.v2.read_secret_version(
            path="vault_secrets/github_details/github_bot",
        )
    except InvalidPath as e:
        LOGGER.warning("Error reading github_bot: %s", e)
        LOGGER.info("github_bot secret not found, Skipping GitHub GPG setup")
        return
    except Exception as e:  # pylint: disable=broad-except
        LOGGER.error("Error reading secret github_bot: %s", e)
        raise ValueError("Error reading secret github_bot") from e

    github_bot_response = secret_version_response["data"]["data"]

    required_keys = ["GH_BOT_API_TOKEN", "GH_BOT_GPG_PRIVATE_KEY", "GH_BOT_GPG_PASSPHRASE"]

    for key in required_keys:
        if key not in github_bot_response:
            LOGGER.warning("%s not found in Vault GitHub secret, Skipping GitHub GPG setup", key)
            return

    fingerprint, ascii_armored_public_keys = get_gpg_public_key_from_private_key(
        private_key=github_bot_response["GH_BOT_GPG_PRIVATE_KEY"],
        passphrase=github_bot_response["GH_BOT_GPG_PASSPHRASE"],
    )

    gpg_key_response = requests.post(
        "https://api.github.com/user/gpg_keys",
        headers={
            "Authorization": f"Bearer {github_bot_response['GH_BOT_API_TOKEN']}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json={"armored_public_key": ascii_armored_public_keys, "name": f"GPG KEY - BOT - {fingerprint}"},
        timeout=30,
    )

    if gpg_key_response.status_code == 422:
        res_json = gpg_key_response.json()
        for error_msg in res_json["errors"]:
            if error_msg["message"] in ["key_id already exists", "public_key already exists"]:
                LOGGER.info("GPG key %s already exists in GitHub", fingerprint)
                return
            LOGGER.error("Error adding GPG key to GitHub: %s", error_msg)
            raise ValueError("Error adding GPG key to GitHub")
    elif gpg_key_response.status_code != 201:
        LOGGER.error("Error adding GPG key to GitHub: %s", gpg_key_response.text)
        raise ValueError("Error adding GPG key to GitHub")


def get_gpg_public_key_from_private_key(private_key: str, passphrase: str) -> Tuple[str, str]:
    """
    This function will get the GPG public key from the private key.
    Args:
        private_key (str): The private key.
        passphrase (str): The passphrase.
    Returns:
        str: The GPG public key.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        gnupg_home = f"{tmp_dir}/.gnupg"
        os.makedirs(gnupg_home, exist_ok=True)
        gpg = gnupg.GPG(gnupghome=gnupg_home)
        gpg.encoding = "utf-8"
        gpg.import_keys(private_key, passphrase=passphrase)
        keys_list = gpg.list_keys(True)
        if len(keys_list) == 0:
            raise ValueError("no keys found")

        if len(keys_list) > 1:
            raise ValueError("multiple keys found")

        fingerprint = keys_list[0]["fingerprint"]
        LOGGER.debug("GPG fingerprint: %s", fingerprint)

        ascii_armored_public_keys = gpg.export_keys(fingerprint)
        LOGGER.debug("GPG public key: %s", ascii_armored_public_keys)

        return fingerprint, ascii_armored_public_keys
