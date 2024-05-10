#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains functions for managing authentication and generating root tokens in HashiCorp Vault.

The functions in this module include:
- add_admin_user_policy: Adds an admin user policy to HashiCorp Vault.
- vault_token_revoke: Revokes all tokens and secret ID accessors in HashiCorp Vault.
- regenerate_root_token: Generates the root token for Vault using the specified raft node and unseal keys.
- _generate_root: Generates the root token using the specified unseal key and nonce.
- _calculate_new_root: Calculates a new root token using the specified encoded root token and OTP.

Note: This module requires the 'hvac' and 'prettytable' libraries to be installed.
"""
import logging
from typing import Any, Dict

from hvac import Client  # type: ignore

from ..models.ha_client import VaultHaClient
from ..models.vault_raft_node_hvac import VaultRaftNodeHvac

LOGGER = logging.getLogger(__name__)


def add_admin_user_policy(ready_node_details: VaultRaftNodeHvac, vault_ha_client: VaultHaClient) -> None:
    """
    Adds an admin user policy to HashiCorp Vault.

    Args:
        ready_node_details (VaultRaftNodeHvac): The details of the HashiCorp Vault Raft node.
        vault_ha_client (VaultHaClient): The HashiCorp Vault client to use for adding the admin user policy.

    Returns:
        None
    """

    client: Client = ready_node_details.hvac_client
    client.sys.create_or_update_policy(
        name=vault_ha_client.policy_name,
        policy='path "*" {capabilities = ["create", "read", "update", "delete", "list", "sudo"]}',
    )

    current_auth_methods: Dict[str, Any] = client.sys.list_auth_methods()["data"]
    if not f"{vault_ha_client.userpass_mount}/" in current_auth_methods:
        LOGGER.info("Creating auth method %s", vault_ha_client.userpass_mount)
        enable_auth_mount_res = client.sys.enable_auth_method(
            method_type="userpass", path=vault_ha_client.userpass_mount
        )
        LOGGER.debug("%s:: Enabled auth mount response: %s", ready_node_details.node_id, enable_auth_mount_res)

    client.sys.tune_auth_method(
        path=vault_ha_client.userpass_mount,
        description="Userpass auth method for admin user",
        default_lease_ttl="1h",
        max_lease_ttl="24h",
    )

    LOGGER.info("Creating %s user", vault_ha_client.admin_user)
    user_create_data = {
        "password": vault_ha_client.admin_password,
        "token_policies": [vault_ha_client.policy_name, "default"],
        "token_ttl": "1h",
    }
    LOGGER.debug("User create data: %s", user_create_data)
    create_new_user = client.write_data(
        path=f"auth/{vault_ha_client.userpass_mount}/users/{vault_ha_client.admin_user}",
        data=user_create_data,
    )
    LOGGER.info("Created %s user: %s", vault_ha_client.admin_user, create_new_user)
