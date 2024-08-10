import os
from typing import Any, Dict, List, Optional, Set

from pydantic import Field, computed_field

from .vault_node import VaultNode


class VaultRaftNode(VaultNode):
    """
    Represents the details of a Vault Raft node.
    Attributes:
        server_name (str): The name of the server.
        node_name (str): The name of the node.
        ha_hostname_san_entry (str): The Subject Alternative Name (SAN) entry for the Vault HA hostname.
        retry_join_nodes (Optional[Dict[str, Any]]): The nodes to retry joining the cluster with.
        vaultops_tmp_dir_path (str): The root directory for storing temporary files.
    """

    server_name: str = Field(...)
    node_name: str = Field(...)
    ha_hostname_san_entry: str = Field(default=...)
    retry_join_nodes: Optional[Dict[str, Any]] = Field(default=None, init_var=False)
    vaultops_tmp_dir_path: str = Field(default=...)

    @computed_field(return_type=str)  # type: ignore
    @property
    def vaultops_raft_node_tmp_dir_path(self) -> str:
        """
        Returns the temporary directory path for the local node in the Vault inventory.

        :return: The temporary directory path for the local node.
        :rtype: str
        """
        __vaultops_raft_node_tmp_dir_path = os.path.join(self.vaultops_tmp_dir_path, self.node_id)
        os.makedirs(__vaultops_raft_node_tmp_dir_path, exist_ok=True)
        return __vaultops_raft_node_tmp_dir_path

    @computed_field(return_type=str)  # type: ignore
    @property
    def api_addr(self) -> str:
        """
        Returns the API address for the Vault inventory builder.

        If `api_ip` is set, it returns the API address using the IP address and node port.
        Otherwise, it returns the API address using the fully qualified domain name (`api_addr_fqdn`) and node port.

        Returns:
            str: The API address for the Vault inventory builder.
        """
        if self.api_ip:
            return f"https://{self.api_ip}:{self.node_port}"
        return f"https://{self.api_addr_fqdn}:{self.node_port}"

    @computed_field(return_type=str)  # type: ignore
    @property
    def cluster_addr(self) -> str:
        """
        Returns the cluster address.

        If the cluster IP is available, it returns the address in the format "https://<cluster_ip>:<cluster_port>".
        Otherwise, it returns the address in the format "https://<cluster_addr_fqdn>:<cluster_port>".

        Returns:
            str: The cluster address.
        """
        if self.cluster_ip:
            return f"https://{self.cluster_ip}:{self.cluster_port}"
        return f"https://{self.cluster_addr_fqdn}:{self.cluster_port}"

    @computed_field(return_type=List[str])  # type: ignore
    @property
    def subject_alt_name(self) -> List[str]:
        """
        Returns a list of subject alternative names (SANs) for the Vault inventory builder.

        The SANs include the HA hostname, API address FQDN, cluster address FQDN,
        API IP address, and cluster IP address.

        Returns:
            List[str]: A list of subject alternative names.
        """
        alt_sub_names: Set[str] = {self.ha_hostname_san_entry}
        if self.api_addr_fqdn:
            alt_sub_names.add(f"DNS:{self.api_addr_fqdn}")
        if self.cluster_addr_fqdn:
            alt_sub_names.add(f"DNS:{self.cluster_addr_fqdn}")
        if self.api_ip:
            alt_sub_names.add(f"IP:{self.api_ip}")
        if self.cluster_ip:
            alt_sub_names.add(f"IP:{self.cluster_ip}")
        return list(alt_sub_names)

    @computed_field(return_type=str)  # type: ignore
    @property
    def node_id(self) -> str:
        """
        Returns the node ID.

        Returns:
            str: The node ID.
        """
        return f"{self.server_name}-{self.node_name}"
