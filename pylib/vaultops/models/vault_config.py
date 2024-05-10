import ipaddress
import os
from typing import Any, Dict, Optional

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
import yaml

from .exit_hook import ExitHooks
from .vault_secrets import VaultSecrets
from .vault_server import VaultServer


class VaultConfig(BaseSettings):
    """
    Represents the secrets required for interacting with HashiCorp Vault.

    Attributes:
        vaultops_tmp_dir_path (str): The root directory for storing temporary files.
        vaultops_config_dir_path (str): The root directory for storing configuration files.
    """

    model_config = SettingsConfigDict(validate_default=False)

    vaultops_tmp_dir_path: str
    vaultops_config_dir_path: str
    vaultops_update_run_id: bool = False

    _secret_file_name: str = "vault_secrets.yml"
    _vault_servers_file_name = "vault_servers.yml"
    _run_id_start_file_name = "run_id_start.txt"
    _run_id_end_file_name = "run_id_end.txt"
    _vault_unseal_keys_file_name = "vault_unseal_keys.yml"
    _hooks = ExitHooks()

    def __init__(self, **data: Any):
        super().__init__(**data)

        if not os.path.isabs(self.vaultops_config_dir_path):
            raise ValueError("vaultops_config_dir_path must be an absolute path")

        if not os.path.isabs(self.vaultops_tmp_dir_path):
            raise ValueError("vaultops_tmp_dir_path must be an absolute path")

        self._hooks.hook()
        _run_id_start_file = os.path.join(self.vaultops_config_dir_path, self._run_id_start_file_name)
        _run_id_end_file = os.path.join(self.vaultops_config_dir_path, self._run_id_end_file_name)
        _run_id_start: int = 0
        _run_id_end: int = 0

        if os.path.exists(_run_id_start_file):
            with open(_run_id_start_file, "r", encoding="utf-8") as f:
                _run_id_start = int(f.read())

        if os.path.exists(_run_id_end_file):
            with open(_run_id_end_file, "r", encoding="utf-8") as f:
                _run_id_end = int(f.read())

        if _run_id_start != _run_id_end:
            raise ValueError("Run ID start and end do not match")

        self._tf_state_file = os.path.join(
            self.vaultops_config_dir_path, "tfstate", f"terraform-{_run_id_start}.tfstate"
        )

        self._run_id = _run_id_start + 1

        self._next_tf_state_file = os.path.join(
            self.vaultops_config_dir_path, "tfstate", f"terraform-{self._run_id}.tfstate"
        )
        self._raft_snapshot_file = os.path.join(
            self.vaultops_config_dir_path, "vault-raft-snapshot", f"vault-raft-snapshot-{self._run_id}.snap"
        )

        if self._run_id > 2 and self.get_codifiedvault_tf_state() is None:
            raise ValueError("Terraform state file not found but run ID is greater than 2")

        if self._run_id > 2 and self.get_vault_unseal_keys() is None:
            raise ValueError("Vault unseal keys file not found, but run ID is greater than 2")

        if self.vaultops_update_run_id:
            with open(_run_id_start_file, "w", encoding="utf-8") as f:
                f.write(str(self._run_id))

    def close(self) -> None:
        """
        Close the VaultConfig object.
        """
        if self._hooks.exit_code == 0 and self._hooks.exception is None and self.vaultops_update_run_id:
            _run_id_end_file = os.path.join(self.vaultops_config_dir_path, self._run_id_end_file_name)
            with open(_run_id_end_file, "w", encoding="utf-8") as f:
                f.write(str(self._run_id))

    @computed_field(return_type=Dict[str, VaultServer])  # type: ignore
    @property
    def vault_servers(self) -> Dict[str, VaultServer]:
        """
        Returns the Vault servers.

        Returns:
            Dict[str, VaultServer]: The Vault servers.
        """

        vault_servers_file_path = os.path.join(self.vaultops_config_dir_path, self._vault_servers_file_name)
        with open(vault_servers_file_path, "r", encoding="utf-8") as vault_servers_file:
            servers_dict = yaml.safe_load(vault_servers_file)

        return {name: VaultServer.model_validate(server_dict) for name, server_dict in servers_dict.items()}

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

    def get_codifiedvault_tf_state(self) -> Optional[str]:
        """
        Returns the Terraform state.
        """

        if not os.path.exists(self._tf_state_file):
            return None
        with open(self._tf_state_file, "r", encoding="utf-8") as tf_state_file:
            return tf_state_file.read()

    def set_codifiedvault_tf_state(self, tf_state: str) -> None:
        """
        Sets the Terraform state.

        Args:
            tf_state (str): The Terraform state.
        """

        os.makedirs(os.path.dirname(self._next_tf_state_file), exist_ok=True)
        with open(self._next_tf_state_file, "w", encoding="utf-8") as tf_state_file:
            tf_state_file.write(tf_state)

    def get_vault_unseal_keys(self) -> Optional[Dict[str, str]]:
        """
        Returns the Vault unseal keys.

        Returns:
            Dict[str, str]: The Vault unseal keys.
        """

        if not os.path.exists(self.vault_unseal_keys_path):
            return None

        with open(self.vault_unseal_keys_path, "r", encoding="utf-8") as unseal_keys_file:
            return yaml.safe_load(unseal_keys_file)

    def set_vault_unseal_keys(self, unseal_keys: Dict[str, Any]) -> None:
        """
        Sets the Vault unseal keys.

        Args:
            unseal_keys (Dict[str, str]): The Vault unseal keys.
        """

        os.makedirs(os.path.dirname(self.vault_unseal_keys_path), exist_ok=True)

        with open(self.vault_unseal_keys_path, "w", encoding="utf-8") as unseal_keys_file:
            yaml.dump(unseal_keys, unseal_keys_file)

    @computed_field(return_type=str)  # type: ignore
    @property
    def vault_unseal_keys_path(self):
        """
        Returns the path to the file containing the unseal keys.

        Returns:
            str: The path to the file containing the unseal keys.
        """
        return os.path.join(self.vaultops_config_dir_path, self._vault_unseal_keys_file_name)

    def save_raft_snapshot(self, snapshot: Any) -> None:
        """
        Saves the Raft snapshot to the specified file path.

        Args:
            snapshot: The Raft snapshot to save.
        """
        os.makedirs(os.path.dirname(self._raft_snapshot_file), exist_ok=True)
        with open(self._raft_snapshot_file, "wb") as f:
            f.write(snapshot)

    @computed_field(return_type=VaultSecrets)  # type: ignore
    @property
    def vault_secrets(self) -> VaultSecrets:
        """
        Returns the secrets stored in the file.

        Returns:
            str: The secrets stored in the file.
        """

        secret_file_path = os.path.join(self.vaultops_config_dir_path, self._secret_file_name)
        with open(secret_file_path, "r", encoding="utf-8") as secrets_file:
            return VaultSecrets.model_validate(yaml.safe_load(secrets_file))
