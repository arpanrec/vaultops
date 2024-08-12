#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains functions for managing the raft cluster in HashiCorp Vault.

The functions in this module provide functionality to remove unmatched nodes from the raft cluster,
add new nodes to the existing raft cluster, and validate the raft nodes.

Functions:
- raft_ops: Performs the operations to manage the raft cluster, including removing unmatched nodes,
  adding new nodes, and validating the raft nodes.
- _remove_raft_nodes: Removes raft nodes that are not in the expected list of nodes.
- _add_raft_nodes: Adds new nodes to the existing raft cluster.
- _validate_raft_nodes: Validates the raft nodes.

Classes:
- VaultRaftNodeHvac: Represents a node in the raft cluster.
- VaultOpsRetryError: Custom exception raised when there is an error during raft operations.

Note: This module requires the `hvac` library to be installed.
"""

import json
import logging
from typing import Dict, List
from urllib.parse import urlsplit

import jmespath
from hvac import Client  # type: ignore

from .. import VaultOpsRetryError
from ..models.vault_raft_node_hvac import VaultRaftNodeHvac

LOGGER = logging.getLogger(__name__)


def raft_ops(all_raft_nodes: Dict[str, VaultRaftNodeHvac], ready_node_details: VaultRaftNodeHvac) -> None:
    """
    Performs the necessary operations for managing the Raft nodes in the Vault cluster.

    Args:
        all_raft_nodes (Dict[str, VaultRaftNodeHvac]): A dictionary containing all the Raft nodes in the cluster.
        ready_node_details (VaultRaftNodeHvac): The details of the Raft node that is ready to join the cluster.

    Returns:
        None
    """

    LOGGER.info("Removing unmatched nodes")
    _remove_raft_nodes(all_raft_nodes=all_raft_nodes, ready_node_details=ready_node_details)

    LOGGER.info("adding new nodes")
    _add_raft_nodes(all_raft_nodes=all_raft_nodes, ready_node_details=ready_node_details)

    LOGGER.info("Validating raft nodes")
    _validate_raft_nodes(ready_node_details, all_raft_nodes)
    LOGGER.info("Vault cluster is ready")


def _remove_raft_nodes(ready_node_details: VaultRaftNodeHvac, all_raft_nodes: Dict[str, VaultRaftNodeHvac]) -> None:
    """
    Remove raft nodes that are not in the expected list of nodes.

    :param ready_node_details: The ready node to remove raft nodes from.
    :param all_raft_nodes: The expected list of raft nodes.
    """
    ready_node_client: Client = ready_node_details.hvac_client
    current_raft_server_node_ids = jmespath.search(
        "[*].node_id", ready_node_client.sys.read_raft_config()["data"]["config"]["servers"]
    )
    expected_raft_server_node_ids: List[str] = list(all_raft_nodes.keys())
    for current_raft_server_node_id in current_raft_server_node_ids:
        if current_raft_server_node_id not in expected_raft_server_node_ids:
            LOGGER.warning("Raft server node ids are not matching with expected node %s.", current_raft_server_node_id)
            LOGGER.warning("Removing raft server node id from raft servers.")
            raft_removed_result = ready_node_client.sys.remove_raft_node(current_raft_server_node_id)
            LOGGER.info("Raft removed result: %s", raft_removed_result)


# pylint: disable=too-many-locals
def _add_raft_nodes(ready_node_details: VaultRaftNodeHvac, all_raft_nodes: Dict[str, VaultRaftNodeHvac]) -> None:
    """
    Adds new nodes to the existing raft cluster.

    Args:
        ready_node_details (VaultRaftNodeHvac): The ready node.
        all_raft_nodes (Dict[str, VaultRaftNodeHvac]):
            - List of dictionaries containing information about each node in the raft cluster.
    Raises:
        ValueError: If the number of nodes to be added is less than 1.

    Returns:
        None
    """
    ready_node_client: Client = ready_node_details.hvac_client
    current_raft_servers = ready_node_client.sys.read_raft_config()["data"]["config"]["servers"]
    current_raft_server_node_ids = jmespath.search("[*].node_id", current_raft_servers)
    LOGGER.info("Search leader node id")
    leader_config = jmespath.search("[?leader==`true`]", current_raft_servers)[0]
    LOGGER.info("Leader node id found\n %s", json.dumps(leader_config, indent=4))
    leader_node_id = leader_config["node_id"]

    LOGGER.info("Leader node id: %s", leader_node_id)

    leader_node_details = all_raft_nodes[leader_node_id]
    with open(leader_node_details.client_cert_path, "r", encoding="utf-8") as f:
        leader_client_cert = f.read()
    with open(leader_node_details.client_key_path, "r", encoding="utf-8") as f:
        leader_client_key = f.read()
    with open(leader_node_details.vault_root_ca_cert_file, "r", encoding="utf-8") as f:
        leader_ca_cert = f.read()

    LOGGER.info("Adding raft server node ids to raft servers. leader api addr: %s", leader_node_details.api_addr)
    for raft_node_id, raft_node_details in all_raft_nodes.items():
        if raft_node_id not in current_raft_server_node_ids:
            LOGGER.info("%s:: Adding raft server.", raft_node_id)
            raft_join_status = raft_node_details.hvac_client.sys.join_raft_cluster(
                leader_api_addr=str(leader_node_details.api_addr),
                leader_client_cert=leader_client_cert,
                leader_client_key=leader_client_key,
                leader_ca_cert=leader_ca_cert,
                retry=True,
            )
            LOGGER.info("%s:: Raft join status: %s", raft_node_id, raft_join_status)


def _validate_raft_nodes(leader_node_details: VaultRaftNodeHvac, all_raft_nodes: Dict[str, VaultRaftNodeHvac]) -> None:
    """
    Validates the raft nodes.

    Args:
        leader_node_details (VaultRaftNodeHvac): The leader node details.
        all_raft_nodes (Dict[str, VaultRaftNodeHvac]):
            - List of dictionaries containing information about each node in the raft cluster.

    Raises:
        ValueError: If the number of nodes is less than 1.
    """
    leader_node_client: Client = leader_node_details.hvac_client
    current_raft_servers = leader_node_client.sys.read_raft_config()["data"]["config"]["servers"]

    for current_raft_server in current_raft_servers:
        LOGGER.info("Validating raft server %s", current_raft_server)
        current_node_id = current_raft_server["node_id"]
        if current_node_id not in all_raft_nodes:
            raise VaultOpsRetryError(f"Node ID {current_node_id} not found in current inventory.")
        expected_rafter_node_details: VaultRaftNodeHvac = all_raft_nodes[current_node_id]
        cluster_url_split = urlsplit(expected_rafter_node_details.cluster_addr)
        if f"{cluster_url_split.hostname}:{cluster_url_split.port}" != current_raft_server["address"]:
            raise VaultOpsRetryError(
                f"{current_node_id}:: Cluster address is not matching with expected address "
                f"{cluster_url_split.hostname}:{cluster_url_split.port}, got {current_raft_server['address']}"
            )

    current_raft_server_node_ids = jmespath.search("[*].node_id", current_raft_servers)

    nodes_not_in_current_raft_servers = set(all_raft_nodes.keys()) - set(current_raft_server_node_ids)
    if len(nodes_not_in_current_raft_servers) > 0:
        raise VaultOpsRetryError(f"Nodes {nodes_not_in_current_raft_servers} are not in raft servers.")
