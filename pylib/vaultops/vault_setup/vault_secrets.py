import logging
from typing import Dict, List, Optional, Union

import hvac  # type: ignore
from hvac.exceptions import InvalidPath  # type: ignore

from ..models.ha_client import VaultHaClient
from ..models.vault_config import VaultConfig

LOGGER = logging.getLogger(__name__)


def update_vault_secrets(vault_ha_client: VaultHaClient, vault_config: VaultConfig) -> None:
    """Update external service secrets in Vault.
    Args:
        vault_ha_client (VaultHaClient): Vault HA client.
        vault_config (VaultConfig): Vault configuration.
    """

    client: hvac.Client = vault_ha_client.hvac_client()

    vault_secrets: Dict[str, Union[str, bool, int, Dict]] = vault_config.vault_secrets.model_dump()

    if vault_secrets is None or not isinstance(vault_secrets, dict):
        raise ValueError("Invalid value for external service secrets, it should be instance of dict")

    if len(vault_secrets) == 0:
        return
    __delete_existing_vault_secrets(client, "vault_secrets")
    __create_update_external_services(client, "vault_secrets", vault_secrets)


def __create_update_external_services(client: hvac.Client, key: str, value: Dict) -> None:
    """Create or update external service secrets in Vault.
    Args:
        client (hvac.Client): Vault client.
        key (str): Vault key.
        value (Union[str, bool, int, Dict]): Vault value.
    """

    if value is None or not isinstance(value, dict):
        raise ValueError("Invalid value for external service secrets, it should be instance of dict")

    if value is isinstance(value, dict) and len(value) == 0:
        return

    to_be_created_or_updated_in_this_key: Dict[str, Union[str, bool, int]] = {}
    to_be_created_or_updated_next: Dict[str, Union[dict, str, bool, int]] = {}

    for sub_key, sub_value in value.items():
        if not isinstance(sub_value, dict):
            to_be_created_or_updated_in_this_key[sub_key] = sub_value
        else:
            to_be_created_or_updated_next[sub_key] = sub_value

    if len(to_be_created_or_updated_in_this_key) > 0:
        client.secrets.kv.v2.create_or_update_secret(
            mount_point="vault-secrets",
            path=key,
            secret=to_be_created_or_updated_in_this_key,
        )

    for sub_key, sub_value in to_be_created_or_updated_next.items():
        if sub_key.endswith("/"):
            sub_key = sub_key[:-1]
        if sub_key.startswith("/"):
            sub_key = sub_key[1:]
        __create_update_external_services(client, f"{key}/{sub_key}", sub_value)


def __delete_existing_vault_secrets(client: hvac.Client, key: str) -> None:
    """Delete existing vault secrets.
    Args:
        client (hvac.Client): Vault client.
        key (str): Vault key.
    """

    list_secrets: Optional[List[str]] = None

    try:
        client.secrets.kv.v2.delete_metadata_and_all_versions(
            mount_point="vault-secrets",
            path=key,
        )
        list_secrets = client.secrets.kv.v2.list_secrets(mount_point="vault-secrets", path=key)["data"].get("keys", [])
    except InvalidPath as e:
        LOGGER.info("Vault secret %s not found, skipping deletion, err: %s", key, str(e))
    except Exception as e:  # pylint: disable=broad-except
        raise ValueError(f"Error deleting secret {key}") from e

    LOGGER.info("Deleted secret %s", key)

    if list_secrets is None:
        return

    for secret in list_secrets:
        if secret.endswith("/"):
            secret = secret[:-1]
        if secret.startswith("/"):
            secret = secret[1:]

        __delete_existing_vault_secrets(client, f"{key}/{secret}")
