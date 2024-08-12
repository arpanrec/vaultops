import base64
import os
from typing import Any, Dict, Optional

import boto3
from ansible.inventory.data import InventoryData  # type: ignore
from botocore.config import Config
from botocore.exceptions import ClientError
from botocore.response import StreamingBody
from mypy_boto3_s3.type_defs import GetObjectOutputTypeDef
from pydantic import BaseModel


class StorageConfig(BaseModel):
    """
    Represents the secrets required for interacting with HashiCorp Vault.

    Attributes:
        type: The type of storage.
        option: The storage options.
    """

    type: str
    option: Dict

    def storage_ops(self, *args: Any, **kwargs: Any) -> Optional[str]:
        """
        Args:
            *args: Any
            **kwargs: Any
        Returns:
            Optional[str]: The content of the file.
        """
        if self.type == "s3":
            return self.__s3_storage_ops(*args, **kwargs)

        if self.type == "local":
            return self.__local_storage_ops(*args, **kwargs)

        raise ValueError("Invalid storage type")

    def __s3_storage_ops(  # pylint: disable=too-many-arguments,too-many-locals
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
        vaultops_s3_aes256_sse_customer_key = base64.b64decode(
            self.option["vaultops_s3_aes256_sse_customer_key_base64"]
        ).decode("utf-8")

        __s3_client = boto3.client(
            service_name="s3",
            endpoint_url=self.option["vaultops_s3_endpoint_url"],
            aws_access_key_id=self.option["vaultops_s3_access_key"],
            aws_secret_access_key=self.option["vaultops_s3_secret_key"],
            aws_session_token=None,
            config=Config(
                signature_version=self.option.get("vaultops_s3_signature_version", "s3v4"),
                retries={"max_attempts": 3, "mode": "standard"},
            ),
            verify=True,
        )

        get_bucket_versioning_response = __s3_client.get_bucket_versioning(
            Bucket=self.option["vaultops_s3_bucket_name"],
        )
        if get_bucket_versioning_response.get("Status", "") != "Enabled":
            raise ValueError("Bucket Versioning is not enabled")

        if file_content:
            __s3_client.put_object(
                Bucket=self.option["vaultops_s3_bucket_name"],
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
                Bucket=self.option["vaultops_s3_bucket_name"],
                Key=file_path,
                SSECustomerAlgorithm="AES256",
                SSECustomerKey=vaultops_s3_aes256_sse_customer_key,
                ChecksumMode="ENABLED",
            )
            body: StreamingBody = response["Body"]
            return body.read().decode("utf-8")
        except ClientError as e:
            if (not error_on_missing_file) and e.response["Error"]["Code"] == "NoSuchKey":
                return None
            raise ValueError("S3 Client Error") from e
        except Exception as e:
            raise ValueError("Error reading file from S3") from e

    def __local_storage_ops(  # pylint: disable=too-many-arguments
        self,
        file_path: str,
        file_content: Optional[bytes] = None,
        content_type="text/plain",  # pylint: disable=unused-argument
        content_encoding="utf-8",  # pylint: disable=unused-argument
        content_language="en",  # pylint: disable=unused-argument
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
        vault_file_path = os.path.join(self.option["path"], file_path)
        if file_content is None:
            if not os.path.exists(vault_file_path):
                if error_on_missing_file:
                    raise FileNotFoundError(f"File not found at path: {vault_file_path}")
                return None
            with open(vault_file_path, "r", encoding="utf-8") as file:
                return file.read()
        try:
            base_dir = os.path.dirname(vault_file_path)
            os.makedirs(base_dir, exist_ok=True)
            with open(vault_file_path, "wb") as file:
                file.write(file_content)
            return None
        except Exception as e:
            raise ValueError("Error reading file") from e

    def add_to_ansible_inventory(self, inventory: InventoryData) -> None:
        """
        Add the Vault configuration to the Ansible inventory file.

        Args:
            inventory: The path to the Ansible inventory file.
        """
