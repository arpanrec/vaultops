import logging

from ..models.vault_config import VaultConfig
from ..models.ha_client import VaultHaClient

LOGGER = logging.getLogger(__name__)


def take_raft_snapshot(vault_ha_client: VaultHaClient, vault_config: VaultConfig) -> None:
    """
    Takes a snapshot of the HashiCorp Vault Raft cluster.

    Args:
        vault_ha_client (VaultHaClient): The HashiCorp Vault HA client.
        vault_config (VaultConfig): The HashiCorp Vault configuration.

    Returns:
        None
    """

    client = vault_ha_client.hvac_client()
    snapshot_res = client.read(
        path="/sys/storage/raft/snapshot",
    )

    vault_config.save_raft_snapshot(snapshot_res.content)
