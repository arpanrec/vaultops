#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains the function to find the first ready raft node from the given list of raft nodes.
"""
import logging
from typing import Dict, Tuple

from requests import Response

from .. import VaultOpsRetryError
from ..models.vault_raft_node_hvac import VaultRaftNodeHvac

LOGGER = logging.getLogger(__name__)


def find_ready(all_raft_nodes: Dict[str, VaultRaftNodeHvac]) -> Tuple[str, VaultRaftNodeHvac]:
    """
    Finds the first ready raft node from the given list of raft nodes.

    Args:
        all_raft_nodes (Dict[str, VaultRaftNodeHvac]): List of raft nodes.

    Returns:
        Tuple[str, VaultRaftNodeHvac]: The first ready raft node, or None if no ready node is found.
    """
    for raft_node_id, raft_node_details in all_raft_nodes.items():
        client = raft_node_details.hvac_client
        LOGGER.info("%s:: Checking if Vault is ready...", raft_node_id)
        LOGGER.info("%s:: Vault status code: %s", raft_node_id, client.sys.read_health_status())
        node_status_response = client.sys.read_health_status(method="GET")
        if isinstance(node_status_response, Response):
            node_status = node_status_response.json()
        else:
            node_status = node_status_response
        LOGGER.info("%s:: Vault status: %s", raft_node_id, node_status)
        if (
            node_status["initialized"] and (not node_status["sealed"]) and (not node_status["standby"])
        ) or client.sys.read_health_status() == 200:  # and (not node_status.get("standby", False))
            LOGGER.info("%s:: Vault is ready.", raft_node_id)
            return raft_node_id, raft_node_details

        LOGGER.error("%s:: Vault is not ready.", raft_node_id)
    raise VaultOpsRetryError("No ready node found.")
