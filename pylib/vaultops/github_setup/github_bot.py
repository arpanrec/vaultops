import logging
import os
import tempfile
from typing import Tuple

import gnupg  # type: ignore
import requests

from ..models.ha_client import VaultHaClient

LOGGER = logging.getLogger(__name__)


def add_gpg_to_bot_github(vault_ha_client: VaultHaClient):
    """
    This function will GPG public key to the GitHub account.
    Args:
        vault_ha_client (VaultHaClient): The vault client.
    """

    client = vault_ha_client.hvac_client()
    bot_gpg_key = client.secrets.kv.v2.read_secret_version(
        path="vault_secrets/bot_gpg_key",
        mount_point="vault-secrets",
    )["data"]["data"]

    github_bot = client.secrets.kv.v2.read_secret_version(
        path="vault_secrets/github_details/github_bot",
        mount_point="vault-secrets",
    )["data"]["data"]

    fingerprint, ascii_armored_public_keys = get_gpg_public_key_from_private_key(
        private_key=bot_gpg_key["BOT_GPG_PRIVATE_KEY"],
        passphrase=bot_gpg_key["BOT_GPG_PASSPHRASE"],
    )

    gpg_key_response = requests.post(
        "https://api.github.com/user/gpg_keys",
        headers={
            "Authorization": f"Bearer {github_bot['GH_BOT_API_TOKEN']}",
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
