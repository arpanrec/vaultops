import ipaddress
import os
from typing import Any, Dict, Optional

import yaml
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .storage import StorageConfig
from .vault_secrets import VaultSecrets
from .vault_server import VaultServer


class VaultConfig(BaseSettings, extra="allow"):
    """
    Represents the secrets required for interacting with HashiCorp Vault.

    Attributes:
        vaultops_tmp_dir_path (str): The root directory for storing temporary files.
        storage_config (StorageConfig): The storage configuration.
        vault_config (Dict[str, Any]): The Vault configuration dictionary.
    """

    model_config = SettingsConfigDict(validate_default=False)

    vaultops_tmp_dir_path: str = Field(description="The root directory for storing temporary files")
    storage_config: StorageConfig
    vault_config: Dict[str, Any]
    run_id: str

    def __init__(self, **data: Any):
        super().__init__(**data)
        if not os.path.isabs(self.vaultops_tmp_dir_path):
            raise ValueError("vaultops_tmp_dir_path must be an absolute path")

    @computed_field(return_type=str)  # type: ignore
    @property
    def vault_ha_hostname_san_entry(self) -> str:
        """
        Returns the Subject Alternative Name (SAN) entry for the Vault HA hostname.

        If the Vault HA hostname is a valid IP address, the SAN entry will be in the format "IP:<ip_address>".
        If the Vault HA hostname is a valid DNS name, the SAN entry will be in the format "DNS:<dns_name>".

        Returns:
            str: The SAN entry for the Vault HA hostname.

        Raises:
            ValueError: If the Vault HA hostname is neither a valid IP address nor a valid DNS name.
            Exception: If any other exception occurs during the validation process.
        """
        try:
            ipaddress.ip_address(self.vault_secrets.vault_ha_hostname)
            return f"IP:{self.vault_secrets.vault_ha_hostname}"
        except ValueError:
            return f"DNS:{self.vault_secrets.vault_ha_hostname}"
        except Exception as e:
            raise e

    @computed_field(return_type=VaultSecrets)  # type: ignore
    @property
    def vault_secrets(self) -> VaultSecrets:
        """
        Returns the secrets stored in the file.

        Returns:
            VaultSecrets: The secrets stored in the file.
        """

        return VaultSecrets.model_validate(self.vault_config["vault_secrets"])

    @computed_field(return_type=Dict[str, VaultServer])  # type: ignore
    @property
    def vault_servers(self) -> Dict[str, VaultServer]:
        """
        Returns the Vault servers.

        Returns:
            Dict[str, VaultServer]: The Vault servers.
        """

        return {
            name: VaultServer.model_validate(server_dict)
            for name, server_dict in self.vault_config["vault_servers"].items()
        }

    def tf_state(self, state: Optional[str] = None) -> Optional[str]:
        """
        Returns True if the Terraform state file is present; otherwise, returns False.
        """
        if state:
            self.storage_config.storage_ops(
                file_path="terraform-latest.tfstate.json",
                file_content=state.encode("utf-8"),
                content_type="application/json",
            )
            self.storage_config.storage_ops(
                file_path=f"terraform-{self.run_id}.tfstate.json",
                file_content=state.encode("utf-8"),
                content_type="application/json",
            )
            return state
        con_str: Optional[str] = self.storage_config.storage_ops(
            file_path="terraform-latest.tfstate.json",
            error_on_missing_file=False,
        )
        return con_str

    def unseal_keys(self, unseal_keys: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, str]]:
        """
        Returns the Vault unseal keys.

        Returns:
            Dict[str, str]: The Vault unseal keys.
        """
        __vault_unseal_keys_key = "vault_unseal_keys.yml"
        if unseal_keys:
            self.storage_config.storage_ops(
                file_path=__vault_unseal_keys_key,
                file_content=yaml.dump(unseal_keys).encode("utf-8"),
                content_type="text/yaml",
            )
            return unseal_keys
        con_str: Optional[str] = self.storage_config.storage_ops(
            file_path=__vault_unseal_keys_key,
            error_on_missing_file=False,
        )
        if not con_str:
            return None
        return yaml.safe_load(str(con_str))

    def save_raft_snapshot(self, snapshot: bytes) -> None:
        """
        Saves the Raft snapshot to the specified file path.

        Args:
            snapshot: The Raft snapshot to save.
        """

        if isinstance(snapshot, bytes):
            self.storage_config.storage_ops(
                file_path=f"vault-raft-snapshot-{self.run_id}.snap",
                file_content=snapshot,
                content_type="application/octet-stream",
            )
            self.storage_config.storage_ops(
                file_path="vault-raft-snapshot-latest.snap",
                file_content=snapshot,
                content_type="application/octet-stream",
            )
        else:
            raise ValueError("Snapshot must be a bytes object")
