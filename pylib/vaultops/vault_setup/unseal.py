#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module provides a function to unseal Vault on all sealed nodes in a raft cluster using the provided unseal keys.

The unseal_vault function takes the following parameters:
- all_raft_nodes: A dictionary containing information about each node in the raft cluster.
- unseal_keys: A list of unseal keys for unsealing Vault.

The function iterates over each node in the raft cluster and checks if Vault is sealed.
If Vault is already unsealed or not initialized, it skips the unsealing process.
If Vault is sealed and initialized, it attempts to unseal Vault using the provided unseal keys.
If the unsealing is successful, it logs that Vault is unsealed.
Otherwise, it logs a warning that Vault is still sealed even after trying to unseal.

Note: This module requires the 'requests' library and the 'VaultRaftNodeHvac' class from the same package.

Example usage:
unseal_vault(all_raft_nodes, unseal_keys)
"""

import base64
import logging
from typing import Any, Dict, List, Optional

from requests import Response

from .. import VaultOpsRetryError
from ..models.vault_config import VaultConfig
from ..models.vault_raft_node_hvac import VaultRaftNodeHvac

LOGGER = logging.getLogger(__name__)


def unseal_vault(
    all_raft_nodes: Dict[str, VaultRaftNodeHvac],
    vault_config: VaultConfig,
) -> None:
    """
    Unseals Vault on all sealed nodes in the raft cluster using the provided unseal keys.

    Args:
        all_raft_nodes (Dict[str, VaultRaftNodeHvac]):
            - Dictionary containing information about each node in the raft cluster.
        vault_config (VaultConfig): VaultConfig object containing unseal keys.

    Returns:
        None
    """

    for raft_node_id, raft_node_details in all_raft_nodes.items():
        LOGGER.info("%s:: Checking if Vault is sealed...", raft_node_id)
        client = raft_node_details.hvac_client
        node_status_response = client.sys.read_health_status(method="GET")

        if isinstance(node_status_response, Response):
            node_health = node_status_response.json()
        else:
            node_health = node_status_response

        if not node_health["sealed"] and node_health["initialized"]:
            LOGGER.info("%s:: Vault is already unsealed.", raft_node_id)
            continue

        if not node_health["initialized"]:
            LOGGER.info("%s:: Vault is not initialized. Skipping unsealing.", raft_node_id)
            continue

        if node_health["sealed"] and node_health["initialized"]:
            LOGGER.info("%s:: Vault is sealed. Unsealing...", raft_node_id)

            # pylint: disable=R0801
            vault_cluster_keys: Optional[Dict[str, Any]] = vault_config.unseal_keys()
            if vault_cluster_keys is None:
                raise VaultOpsRetryError("Vault cluster unseal keys not found in secrets.")

            keys_base64: List[str] = vault_cluster_keys["keys_base64"]
            unseal_keys: List[str] = [
                base64.b64decode(unseal_key, altchars=None, validate=False).hex() for unseal_key in list(keys_base64)
            ]

            unseal_response = client.sys.submit_unseal_keys(keys=unseal_keys)
            if unseal_response["sealed"] is False:
                LOGGER.info("%s:: Vault is unsealed.", raft_node_id)
            else:
                LOGGER.warning("%s:: Vault is still sealed even after trying to unseal.", raft_node_id)
