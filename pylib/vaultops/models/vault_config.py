import base64
import hashlib
import ipaddress
import os
from typing import Any, Dict, Optional

import boto3
import yaml
from botocore.config import Config
from mypy_boto3_s3.client import S3Client
from mypy_boto3_s3.type_defs import GetBucketLocationOutputTypeDef
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

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
        vaultops_s3_region (str): The region of the S3 bucket.
    """

    model_config = SettingsConfigDict(validate_default=False)

    vaultops_tmp_dir_path: str
    vaultops_s3_aes256_sse_customer_key_base64: str
    vaultops_s3_bucket_name: str
    vaultops_s3_endpoint_url: str
    vaultops_s3_access_key: str
    vaultops_s3_secret_key: str
    vaultops_s3_signature_version: str = Field(default="s3v4", description="The signature version for the S3 bucket")
    vaultops_s3_region: str = Field(description="The region of the S3 bucket")

    __vault_config_key = "vault_config.yml"
    __vault_unseal_keys_key = "vault_unseal_keys.yml"
    __vault_terraform_state_key = "terraform.tfstate"
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
            config=Config(
                signature_version=self.vaultops_s3_signature_version, retries={"max_attempts": 3, "mode": "standard"}
            ),
            verify=True,
        )

        bucket_location: GetBucketLocationOutputTypeDef = self.__s3_client.get_bucket_location(
            Bucket=self.vaultops_s3_bucket_name
        )

        if bucket_location.get("LocationConstraint", "") != self.vaultops_s3_region:
            raise ValueError(f"Bucket Location: {bucket_location} does not match the region: {self.vaultops_s3_region}")

        pre_requisites = yaml.safe_load(self.__read_s3(self.__vault_config_key))
        self.__vault_config_dict.update(pre_requisites)

    @computed_field(return_type=str)  # type: ignore
    @property
    def vaultops_s3_aes256_sse_customer_key(self) -> str:
        """
        Returns the AES256 key for the S3 bucket.

        Returns:
            str: The AES256 key for the S3 bucket.
        """
        return base64.b64decode(self.vaultops_s3_aes256_sse_customer_key_base64).decode("utf-8")

    def __read_s3(self, key: str) -> str:
        """
        Reads the file from the S3 bucket.

        Args:
            key (str): The key of the file to read.

        Returns:
            str: The content of the file.
        """
        response = self.__s3_client.get_object(
            Bucket=self.vaultops_s3_bucket_name,
            Key=key,
            SSECustomerAlgorithm="AES256",
            SSECustomerKey=self.vaultops_s3_aes256_sse_customer_key,
            ChecksumMode="ENABLED",
        )
        return response["Body"].read().decode("utf-8")

    def __write_s3(  # pylint: disable=too-many-arguments
        self, key: str, content: bytes, content_type: str, content_encoding: str = "utf-8", content_language: str = "en"
    ) -> None:
        sha256_hash: str = base64.b64encode(hashlib.sha256(content).digest()).decode("utf-8")
        md5_hash: str = base64.b64encode(hashlib.md5(content).digest()).decode("utf-8")
        self.__s3_client.put_object(
            Bucket=self.vaultops_s3_bucket_name,
            Key=key,
            Body=content,
            Metadata={},
            ContentType=content_type,
            ContentEncoding=content_encoding,
            ContentLanguage=content_language,
            ACL="private",
            ChecksumSHA256=sha256_hash,
            ContentMD5=md5_hash,
            SSECustomerAlgorithm="AES256",
            SSECustomerKey=self.vaultops_s3_aes256_sse_customer_key,
            ContentLength=len(content),
        )

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

    def get_terraform_backend_config(self) -> Dict[str, Any]:
        """
        Returns the Terraform backend configuration.
        """

        return {
            "bucket": self.vaultops_s3_bucket_name,
            "key": self.__vault_terraform_state_key,
            "endpoints": {"s3": self.vaultops_s3_endpoint_url},
            "access_key": self.vaultops_s3_access_key,
            "secret_key": self.vaultops_s3_secret_key,
            "region": self.vaultops_s3_region,
            "skip_credentials_validation": True,
            "skip_metadata_api_check": True,
            "skip_region_validation": True,
            "skip_requesting_account_id": True,
            "use_path_style": True,
            "encrypt": True,
            "sse_customer_key": self.vaultops_s3_aes256_sse_customer_key_base64,
        }

    def unseal_keys(self, unseal_keys: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, str]]:
        """
        Returns the Vault unseal keys.

        Returns:
            Dict[str, str]: The Vault unseal keys.
        """

        if unseal_keys is not None:
            self.__write_s3(self.__vault_unseal_keys_key, yaml.dump(unseal_keys).encode("utf-8"), "text/yaml")
            return unseal_keys

        try:
            return yaml.safe_load(self.__read_s3(self.__vault_unseal_keys_key))
        except Exception as e:
            if "The specified key does not exist" in str(e):
                return None
            raise ValueError("Error occurred while reading unseal") from e

    def save_raft_snapshot(self, snapshot: bytes) -> None:
        """
        Saves the Raft snapshot to the specified file path.

        Args:
            snapshot: The Raft snapshot to save.
        """
        print("snapshot: ", snapshot, type(snapshot))
        if isinstance(snapshot, bytes):
            self.__write_s3(self.__vault_config_key, snapshot, "application/octet-stream")

        raise ValueError("Snapshot must be a bytes object")

    @computed_field(return_type=VaultSecrets)  # type: ignore
    @property
    def vault_secrets(self) -> VaultSecrets:
        """
        Returns the secrets stored in the file.

        Returns:
            VaultSecrets: The secrets stored in the file.
        """

        return VaultSecrets.model_validate(self.__vault_config_dict["vault_secrets"])
