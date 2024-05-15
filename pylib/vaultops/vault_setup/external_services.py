from typing import Dict, Union

import hvac  # type: ignore

from ..models.ha_client import VaultHaClient
from ..models.vault_config import VaultConfig


def update_external_services(vault_ha_client: VaultHaClient, vault_config: VaultConfig) -> None:
    """Update external service secrets in Vault.
    Args:
        vault_ha_client (VaultHaClient): Vault HA client.
        vault_config (VaultConfig): Vault configuration.
    """

    client: hvac.Client = vault_ha_client.hvac_client()
    external_services: Dict[str, Union[str, bool, int, Dict]] = vault_config.vault_secrets.external_services

    if external_services is None or not isinstance(external_services, dict):
        raise ValueError("Invalid value for external service secrets, it should be instance of dict")

    if len(external_services) == 0:
        return

    __create_update_external_services(client, "external_services", external_services)


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
            mount_point="secret",
            path=key,
            secret=to_be_created_or_updated_in_this_key,
        )

    for sub_key, sub_value in to_be_created_or_updated_next.items():
        __create_update_external_services(client, f"{key}/{sub_key}", sub_value)
