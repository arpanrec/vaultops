#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains the function to initialize Vault on the first node in
the raft_nodes list if it is not already initialized.
It also saves the initialization secrets to the specified file.

The module includes the following functions:
- initialize_vault: Initializes Vault and saves the initialization secrets.

"""
import logging
from typing import Dict

import hvac  # type: ignore
import yaml

from .. import VaultOpsRetryError, VaultOpsSafeExit
from ..models.vault_config import VaultConfig
from ..models.vault_raft_node_hvac import VaultRaftNodeHvac

LOGGER = logging.getLogger(__name__)


def initialize_vault(all_raft_nodes: Dict[str, VaultRaftNodeHvac], vault_config: VaultConfig):
    """
    Initializes Vault on the first node in the raft_nodes list if it is not already initialized.
    Saves the initialization secrets to the specified file.

    Args:
        all_raft_nodes (Dict[str, VaultRaftNodeHvac]): Dictionary of all the raft nodes.
        vault_config (VaultConfig): The VaultConfig object.
    Returns:
        None
    """

    if_any_node_is_initialized = False
    for node_id, raft_node in all_raft_nodes.items():
        if raft_node.hvac_client.sys.is_initialized() is True:
            LOGGER.info("%s:: Vault is already initialized.", node_id)
            if_any_node_is_initialized = True
            break
    if if_any_node_is_initialized:
        return

    if vault_config.unseal_keys():
        raise VaultOpsRetryError("Vault is not initialized but unseal keys are provided.")

    if vault_config.tf_state():
        raise VaultOpsRetryError("Terraform state file already exists")

    init_node_id = list(all_raft_nodes.keys())[0]
    init_node = all_raft_nodes[init_node_id]
    LOGGER.info("%s:: Vault is not initialized. Initializing...", init_node_id)
    LOGGER.info("%s:: Saving vault init keys to %s", init_node_id, vault_config.storage_config.type)

    user_wants_to_continue = input("Do you want to continue? type 'yes' to continue: ")
    vault_client: hvac.Client = init_node.hvac_client

    if user_wants_to_continue.lower() != "yes":
        LOGGER.info("Exiting the initialization process.")
        raise VaultOpsSafeExit("Exiting the initialization process.")

    vault_key_shares = int(input("Enter the number of key shares: "))
    vault_key_threshold = int(input("Enter the number of key threshold: "))

    LOGGER.info("Initializing Vault with %s key shares and %s key threshold.", vault_key_shares, vault_key_threshold)

    if vault_key_shares < 1 or vault_key_threshold < 1:
        LOGGER.error("Key shares and key threshold must be greater than 0.")
        raise ValueError("Key shares and key threshold must be greater than 0.")

    if vault_key_shares < vault_key_threshold:
        LOGGER.error("Key shares must be greater than or equal to key threshold.")
        raise ValueError("Key shares must be greater than or equal to key threshold.")

    init_response = vault_client.sys.initialize(secret_shares=vault_key_shares, secret_threshold=vault_key_threshold)
    LOGGER.info("%s:: Vault is initialized.", init_node_id)
    LOGGER.debug("%s:: Vault init response: %s", init_node_id, yaml.dump(data=init_response, default_flow_style=False))

    vault_config.unseal_keys(init_response)
    LOGGER.info("%s:: Vault init secrets are saved in %s", init_node_id, vault_config.unseal_keys())

    if vault_client.sys.is_initialized():
        LOGGER.info("%s:: Vault initialization is complete.", init_node_id)
    else:
        LOGGER.error("%s:: Vault initialization failed.", init_node_id)
        raise VaultOpsRetryError(f"{init_node_id}:: Vault initialization failed.")

    LOGGER.info("Vault initialization is complete.")
