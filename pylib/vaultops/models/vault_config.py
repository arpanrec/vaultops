import base64
import ipaddress
import os
from typing import Any, Dict, Optional

import boto3
import yaml
from pydantic import computed_field, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from mypy_boto3_s3.client import S3Client
from botocore.config import Config

from .vault_secrets import VaultSecrets
from .vault_server import VaultServer


class VaultConfig(BaseSettings):
    """
    Represents the secrets required for interacting with HashiCorp Vault.

    Attributes:
        vaultops_tmp_dir_path (str): The root directory for storing temporary files.
        vaultops_s3_aes256_sse_customer_key_base64 (str):
            - The base64-encoded AES256 key for the S3 bucket.
        vaultops_s3_bucket_name (str): The name of the S3 bucket.
        vaultops_s3_endpoint_url (str): The endpoint URL of the S3 bucket.
        vaultops_s3_access_key (str): The access key for the S3 bucket.
        vaultops_s3_secret_key (str): The secret key for the S3 bucket.
        vaultops_s3_signature_version (str): The signature version for the S3 bucket.
    """

    model_config = SettingsConfigDict(validate_default=False)

    vaultops_tmp_dir_path: str
    vaultops_s3_aes256_sse_customer_key_base64: str
    vaultops_s3_bucket_name: str
    vaultops_s3_endpoint_url: str
    vaultops_s3_access_key: str
    vaultops_s3_secret_key: str
    vaultops_s3_signature_version: str = Field(default="s3v4", description="The signature version for the S3 bucket")

    __vault_config_key = "vault_config.yml"
    __vault_unseal_keys_key = "vault_unseal_keys.yml"
    __vault_config_dict: Dict[str, Any] = {}
    __s3_client: S3Client

    def __init__(self, **data: Any):
        super().__init__(**data)

        if not os.path.isabs(self.vaultops_tmp_dir_path):
            raise ValueError("vaultops_tmp_dir_path must be an absolute path")

        self.__s3_client = boto3.client(
            service_name="s3",
            endpoint_url=self.vaultops_s3_endpoint_url,
            aws_access_key_id=self.vaultops_s3_access_key,
            aws_secret_access_key=self.vaultops_s3_secret_key,
            aws_session_token=None,
            config=Config(signature_version=self.vaultops_s3_signature_version,
                          retries={"max_attempts": 3, "mode": "standard"}),
            verify=True,
        )

        pre_requisites = yaml.safe_load(f)
        self.__vault_config_dict.update(pre_requisites)

    def __read_s3_file(self, key: str) -> str:
        """
        Reads the file from the S3 bucket.

        Args:
            key (str): The key of the file to read.

        Returns:
            str: The content of the file.
        """
        sse_customer_key: str = base64.b64decode(self.vaultops_s3_aes256_sse_customer_key_base64).decode("utf-8")
        response = self.__s3_client.get_object(
            Bucket=self.vaultops_s3_bucket_name, Key=key,
            SSECustomerAlgorithm="AES256",
            SSECustomerKey=sse_customer_key,
            ChecksumMode="ENABLED",
        )
        return response["Body"].read().decode("utf-8")

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
            for name, server_dict in self.__vault_config_dict["vault_servers"].items()
        }

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
            VaultSecrets: The secrets stored in the file.
        """

        vault_secrets = self.__vault_config_dict["vault_secrets"]
        return VaultSecrets.model_validate(vault_secrets)
