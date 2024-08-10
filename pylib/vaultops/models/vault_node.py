from typing import Dict, Optional

from pydantic import BaseModel, Field


class VaultNode(BaseModel):
    """
    Represents the details of a Vault server node.

    Attributes:
        node_port (int): The port number of the node.
        cluster_port (int): The port number of the cluster.
        api_addr_fqdn (str, optional): The fully qualified domain name (FQDN) of the API address.
        api_ip (str, optional): The IP address of the API.
        cluster_addr_fqdn (str, optional): The fully qualified domain name (FQDN) of the cluster address.
        cluster_ip (str, optional): The IP address of the cluster.
        explicit_retry_join_nodes (Dict[str, None], optional): The nodes to retry joining the cluster with.
    """

    node_port: int = Field(...)
    cluster_port: int = Field(...)
    api_addr_fqdn: Optional[str] = Field(default=None)
    api_ip: Optional[str] = Field(default=None)
    cluster_addr_fqdn: Optional[str] = Field(default=None)
    cluster_ip: Optional[str] = Field(default=None)
    explicit_retry_join_nodes: Dict[str, None] | None = Field(default={}, init_var=False)
