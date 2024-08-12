from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from .vault_node import VaultNode


class VaultServer(BaseModel):
    """
    Represents the details of a Vault server.

    Attributes:
        cluster_addr_fqdn (str, optional): The fully qualified domain name of the cluster address.
        cluster_ip (str, optional): The IP address of the cluster.
        api_addr_fqdn (str, optional): The fully qualified domain name of the API address.
        api_ip (str, optional): The IP address of the API.
        vault_nodes (Dict[str, VaultNode]): A dictionary of Vault server node details.
        ansible_opts (Dict[str, str], optional): Additional Ansible options for the Vault server.
        host_keys (List[str], optional): A list of host keys for the Vault server.
        root_ca_key_pem_as_ansible_priv_ssh_key (bool): Whether to use the root CA key as an Ansible private SSH key.
    """

    cluster_addr_fqdn: Optional[str] = Field(default=None)
    cluster_ip: Optional[str] = Field(default=None)
    api_addr_fqdn: Optional[str] = Field(default=None)
    api_ip: Optional[str] = Field(default=None)
    vault_nodes: Dict[str, VaultNode] = Field(...)
    ansible_opts: Dict[str, str] = Field(default={})
    host_keys: List[str] = Field(default=[])
    root_ca_key_pem_as_ansible_priv_ssh_key: bool = Field(default=True)
