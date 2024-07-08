import base64
import ipaddress
import os
from typing import Any, Dict, Optional, Literal

import boto3
import yaml
from botocore.config import Config
from botocore.exceptions import ClientError
from botocore.response import StreamingBody
from mypy_boto3_s3.type_defs import GetBucketLocationOutputTypeDef, GetObjectOutputTypeDef
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .vault_secrets import VaultSecrets
from .vault_server import VaultServer


class VaultConfig(BaseSettings, extra="allow"):
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
        vaultops_s3_skip_region_validation (bool): Whether to skip region validation.
        vaultops_s3_s3_skip_metadata_api_check (bool): Whether to skip metadata API check.
        vaultops_s3_skip_credentials_validation (bool): Whether to skip credentials validation.
        vaultops_s3_skip_requesting_account_id (bool): Whether to skip requesting the account ID.
        vaultops_s3_addressing_style (str): The addressing style for the S3 bucket.
    """

    model_config = SettingsConfigDict(validate_default=False)

    vaultops_tmp_dir_path: str
    vaultops_s3_aes256_sse_customer_key_base64: str
    vaultops_s3_bucket_name: str
    vaultops_s3_endpoint_url: str
    vaultops_s3_access_key: str
    vaultops_s3_secret_key: str
    vaultops_s3_signature_version: str = Field(default="s3v4", description="The signature version for the S3 bucket")
    vaultops_s3_region: str = Field(description="The region of the S3 bucket", default="main")
    vaultops_s3_skip_region_validation: bool = Field(default=False, description="Whether to skip region validation")
    vaultops_s3_s3_skip_metadata_api_check: bool = Field(
        default=False, description="Whether to skip metadata API check"
    )
    vaultops_s3_skip_credentials_validation: bool = Field(
        default=False, description="Whether to skip credentials validation"
    )
    vaultops_s3_skip_requesting_account_id: bool = Field(
        default=False, description="Whether to skip requesting the account ID"
    )
    vaultops_s3_addressing_style: Literal["virtual", "path"] = Field(
        default="virtual", description="The addressing style for the S3 bucket"
    )

    __vault_config_key = "vault_config.yml"
    __vault_unseal_keys_key = "vault_unseal_keys.yml"
    __vault_terraform_state_key = "terraform.tfstate"
    __vault_raft_snapshot_key = "vault_raft_snapshot.snap"
    __vault_config_dict: Dict[str, Any] = {}

    def __init__(self, **data: Any):
        super().__init__(**data)

        if not os.path.isabs(self.vaultops_tmp_dir_path):
            raise ValueError("vaultops_tmp_dir_path must be an absolute path")

        pre_requisites = yaml.safe_load(str(self.storage_ops(file_path=self.__vault_config_key)))
        self.__vault_config_dict.update(pre_requisites)

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
            "skip_credentials_validation": self.vaultops_s3_skip_credentials_validation,
            "skip_metadata_api_check": self.vaultops_s3_s3_skip_metadata_api_check,
            "skip_region_validation": self.vaultops_s3_skip_region_validation,
            "skip_requesting_account_id": self.vaultops_s3_skip_requesting_account_id,
            "use_path_style": self.vaultops_s3_addressing_style == "path",
            "acl": "private",
            "encrypt": True,
            "sse_customer_key": self.vaultops_s3_aes256_sse_customer_key_base64,
            "skip_s3_checksum": True,  # TODO: Need to check, why not working in linode object storage
        }

    def is_terraform_state_file_present(self) -> bool:
        """
        Returns True if the Terraform state file is present; otherwise, returns False.
        """
        con_str: Optional[str] = self.storage_ops(
            file_path=self.__vault_terraform_state_key,
            error_on_missing_file=False,
        )
        if not con_str:
            return False
        return True

    def unseal_keys(self, unseal_keys: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, str]]:
        """
        Returns the Vault unseal keys.

        Returns:
            Dict[str, str]: The Vault unseal keys.
        """

        if unseal_keys:
            self.storage_ops(
                file_path=self.__vault_unseal_keys_key,
                file_content=yaml.dump(unseal_keys).encode("utf-8"),
                content_type="text/yaml",
            )
            return unseal_keys
        con_str: Optional[str] = self.storage_ops(
            file_path=self.__vault_unseal_keys_key,
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
            self.storage_ops(
                file_path=self.__vault_raft_snapshot_key,
                file_content=snapshot,
                content_type="application/octet-stream",
            )
        else:
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

    def storage_ops(  # pylint: disable=too-many-arguments,too-many-locals
        self,
        file_path: str,
        file_content: Optional[bytes] = None,
        content_type="text/plain",
        content_encoding="utf-8",
        content_language="en",
        error_on_missing_file: bool = True,
    ) -> Optional[str]:
        """
        Perform storage operations.
        Args:
            file_path: Path of the file.
            file_content: Content of the file.
            content_type: Type of the content.
            content_encoding: Encoding of the content.
            content_language: Language of the content.
            error_on_missing_file: Whether to raise an error if the file is missing.
        Returns:
            Optional[str]: The content of the file.
        """
        vaultops_s3_aes256_sse_customer_key = base64.b64decode(self.vaultops_s3_aes256_sse_customer_key_base64).decode(
            "utf-8"
        )
        __s3_client = boto3.client(
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

        if not self.vaultops_s3_skip_region_validation:
            bucket_location: GetBucketLocationOutputTypeDef = __s3_client.get_bucket_location(
                Bucket=self.vaultops_s3_bucket_name
            )
            if bucket_location.get("LocationConstraint", "") != self.vaultops_s3_region:
                raise ValueError(
                    f"Bucket Location: {bucket_location} does not match the region: {self.vaultops_s3_region}"
                )

        get_bucket_versioning_response = __s3_client.get_bucket_versioning(
            Bucket=self.vaultops_s3_bucket_name,
        )
        if get_bucket_versioning_response.get("Status", "") != "Enabled":
            raise ValueError("Bucket Versioning is not enabled")

        if file_content:
            __s3_client.put_object(
                Bucket=self.vaultops_s3_bucket_name,
                Key=file_path,
                Body=file_content,
                ContentType=content_type,
                ContentEncoding=content_encoding,
                ContentLanguage=content_language,
                SSECustomerAlgorithm="AES256",
                SSECustomerKey=vaultops_s3_aes256_sse_customer_key,
            )
            return ""
        try:
            response: GetObjectOutputTypeDef = __s3_client.get_object(
                Bucket=self.vaultops_s3_bucket_name,
                Key=file_path,
                SSECustomerAlgorithm="AES256",
                SSECustomerKey=vaultops_s3_aes256_sse_customer_key,
                ChecksumMode="ENABLED",
            )
            body: StreamingBody = response["Body"]
            return body.read().decode("utf-8")
        except Exception as e:
            if (
                (not error_on_missing_file)
                and isinstance(e, ClientError)
                and e.response["Error"]["Code"] == "NoSuchKey"
            ):
                return None
            raise ValueError("Error reading file from S3") from e
