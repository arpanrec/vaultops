#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module provides classes and functions for interacting with HashiCorp Vault using the HVAC client.

Classes:
- VaultRaftNodeHvac: Represents a Vault Raft node with HVAC client configuration.

Functions:
- find_ready: Finds the first ready raft node from a given list of raft nodes.
- update_client_with_root_token: Creates or updates a client in the OAuth2 provider with the specified client ID,
client secret, scopes, redirect URIs, and API base URL.
"""

import logging
from typing import Dict

from ..models.vault_raft_node_hvac import VaultRaftNodeHvac

LOGGER = logging.getLogger(__name__)


def update_client_with_root_token(all_raft_nodes: Dict[str, VaultRaftNodeHvac], new_root_token: str):
    """
    Creates or updates a client in the OAuth2 provider with the specified client ID, client secret, scopes,
    redirect URIs, and API base URL.

    Args:
        all_raft_nodes (Dict[str, VaultRaftNodeHvac]):
            - List of dictionaries containing information about each node in the raft cluster.
        new_root_token (str, optional): The Vault token to use for authentication.

    Returns:
        dict: A dictionary containing information about the created or updated client.
    """
    for raft_node_id, raft_node_details in all_raft_nodes.items():
        LOGGER.info("%s:: Adding root token", raft_node_id)

        if raft_node_details.hvac_client.sys.is_sealed() or not raft_node_details.hvac_client.sys.is_initialized():
            LOGGER.info("%s:: Vault is sealed or not initialized. Skipping.", raft_node_id)
            continue

        raft_node_details.hvac_client.token = new_root_token
        try:
            LOGGER.info("%s:: Client auth status %s.", raft_node_id, raft_node_details.hvac_client.is_authenticated())
        except Exception as e:  # pylint: disable=broad-except
            LOGGER.exception("%s:: Client is not authenticated. %s.", raft_node_id, str(e))
