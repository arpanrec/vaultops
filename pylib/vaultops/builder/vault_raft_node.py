import ipaddress
from typing import Dict, Optional, Set

from ..models.vault_config import VaultConfig
from ..models.vault_node import VaultNode
from ..models.vault_raft_node import VaultRaftNode
from ..models.vault_server import VaultServer


# pylint: disable=too-many-locals
def build_raft_server_nodes_map(
    vault_config: VaultConfig,
) -> Dict[str, Dict[str, VaultRaftNode]]:
    """
    Build a map of raft nodes for each vault server
    """
    vault_servers: Dict[str, VaultServer] = vault_config.vault_servers
    server_raft_nodes: Dict[str, Dict[str, VaultRaftNode]] = {}
    validation_node_id: Set[str] = set()
    for vault_server_name, vault_server_details in vault_servers.items():
        vault_nodes: Dict[str, VaultNode] = vault_server_details.vault_nodes
        validation_node_port: Set[int] = set()
        server_raft_nodes[vault_server_name] = {}
        for node_name, node_details in vault_nodes.items():
            raft_node: VaultRaftNode = VaultRaftNode(
                server_name=vault_server_name,
                node_name=node_name,
                ha_hostname_san_entry=vault_config.vault_ha_hostname_san_entry,
                vaultops_tmp_dir_path=vault_config.vaultops_tmp_dir_path,
                **node_details.model_dump(),
            )

            api_addr_fqdn: Optional[str] = (
                node_details.api_addr_fqdn if node_details.api_addr_fqdn else vault_server_details.api_addr_fqdn
            )
            api_ip: Optional[str] = node_details.api_ip if node_details.api_ip else vault_server_details.api_ip
            cluster_addr_fqdn: Optional[str] = (
                node_details.cluster_addr_fqdn
                if node_details.cluster_addr_fqdn
                else vault_server_details.cluster_addr_fqdn
            )
            cluster_ip: Optional[str] = (
                node_details.cluster_ip if node_details.cluster_ip else vault_server_details.cluster_ip
            )

            for ip_addr in [api_ip, cluster_ip]:
                if ip_addr:
                    try:
                        ipaddress.ip_address(ip_addr)
                    except Exception as e:
                        raise ValueError(
                            f"Vault Server: {vault_server_name}, Vault Node: {node_name}, {ip_addr} "
                            f"is not a valid IP address"
                        ) from e

            if not api_addr_fqdn and not api_ip:
                raise ValueError(
                    f"Vault Server: {vault_server_name}, Vault Node: {node_name}, api_addr_fqdn or api_ip are required"
                )
            if not cluster_addr_fqdn and not cluster_ip:
                raise ValueError(
                    f"Vault Server: {vault_server_name}, Vault Node: {node_name}, "
                    f"cluster_addr_fqdn or cluster_ip are required"
                )
            raft_node.api_addr_fqdn = api_addr_fqdn
            raft_node.api_ip = api_ip
            raft_node.cluster_addr_fqdn = cluster_addr_fqdn
            raft_node.cluster_ip = cluster_ip
            if (
                (node_details.node_port in validation_node_port)
                or (node_details.cluster_port in validation_node_port)
                or (node_details.node_port == node_details.cluster_port)
            ):
                raise ValueError(
                    f"Vault Server: {vault_server_name}, Vault Node: {node_name}, "
                    f"node_port {node_details.node_port} or cluster_port {node_details.cluster_port} is already in use"
                )
            validation_node_port.add(node_details.node_port)
            validation_node_port.add(node_details.cluster_port)

            if vault_server_name + "-" + node_name in validation_node_id:
                raise ValueError(
                    f"Vault Server: {vault_server_name}, "
                    f"Vault Node: {node_name}, node_id {vault_server_name + '-' + node_name} is already in use"
                )
            validation_node_id.add(vault_server_name + "-" + node_name)

            server_raft_nodes[vault_server_name][vault_server_name + "-" + node_name] = raft_node
    return server_raft_nodes
