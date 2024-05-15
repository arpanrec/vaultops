import logging
from typing import Dict

from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes
from cryptography.x509 import Certificate

from ..models.vault_config import VaultConfig
from ..models.vault_raft_node import VaultRaftNode
from ..models.vault_raft_node_hvac import VaultRaftNodeHvac
from .vault_raft_node import build_raft_server_nodes_map

LOGGER = logging.getLogger(__name__)


def create_raft_node_hvac(
    vault_config: VaultConfig,
    rsa_root_ca_key: PrivateKeyTypes,
    rsa_root_ca_cert: Certificate,
    vault_root_ca_cert_file: str,
) -> Dict[str, VaultRaftNodeHvac]:
    """
    Creates an HVAC client based on the provided inventory file.

    Args:
        vault_config (VaultConfig): The Vault secrets.
        rsa_root_ca_key (PrivateKeyTypes): The private key of the root CA used for signing the certificates.
        rsa_root_ca_cert (Certificate): The root CA certificate used for signing the certificates.
        vault_root_ca_cert_file (str): The path to the file containing the root CA certificate.

    Returns:
        Dict[str, VaultRaftNodeHvac]: A dictionary containing information about each node in the raft cluster.

    Raises:
        Any exceptions that may occur during the execution of the function.
    """

    server_raft_nodes: Dict[str, Dict[str, VaultRaftNode]] = build_raft_server_nodes_map(vault_config)
    all_raft_nodes: Dict[str, VaultRaftNodeHvac] = {}

    for vault_server_raft_nodes in server_raft_nodes.values():
        for node_id, node_details in vault_server_raft_nodes.items():
            all_raft_nodes[node_id] = VaultRaftNodeHvac(
                **node_details.model_dump(),
                vault_root_ca_cert_file=vault_root_ca_cert_file,
                rsa_root_ca_key=rsa_root_ca_key,
                rsa_root_ca_cert=rsa_root_ca_cert,
            )

    LOGGER.info("Creating vault client certificates")

    return all_raft_nodes
