import base64
import json
import os
from typing import Optional

import boto3
from ansible.inventory.data import InventoryData  # type: ignore
from botocore.config import Config
from botocore.exceptions import ClientError
from botocore.response import StreamingBody
from mypy_boto3_s3.type_defs import GetObjectOutputTypeDef
from pydantic import Field, BaseModel
from bitwarden_sdk import BitwardenClient, DeviceType, client_settings_from_dict  # type: ignore


class StorageConfig(BaseModel):
    """
    Represents the secrets required for interacting with HashiCorp Vault.

    Bitwarden Secrets entry:
        {
            "vaultops_s3_aes256_sse_customer_key_base64": "base64-encoded-key",
            "vaultops_s3_bucket_name": "bucket-name",
            "vaultops_s3_endpoint_url": "endpoint-url",
            "vaultops_s3_access_key": "access-key",
            "vaultops_s3_secret_key": "secret-key",
            "vaultops_s3_signature_version": "signature-version",
            "vaultops_s3_region": "region"
        }

    Attributes:
        vaultops_s3_aes256_sse_customer_key_base64 (str):
            - The base64-encoded AES256 key for the S3 bucket.
        vaultops_s3_bucket_name (str): The name of the S3 bucket.
        vaultops_s3_endpoint_url (str): The endpoint URL of the S3 bucket.
        vaultops_s3_access_key (str): The access key for the S3 bucket.
        vaultops_s3_secret_key (str): The secret key for the S3 bucket.
        vaultops_s3_signature_version (str): The signature version for the S3 bucket.
        vaultops_s3_region (str): The region of the S3 bucket.
    """

    vaultops_s3_aes256_sse_customer_key_base64: str = Field(
        description="The base64-encoded AES256 key for the S3 bucket"
    )
    vaultops_s3_bucket_name: str = Field(description="The name of the S3 bucket")
    vaultops_s3_endpoint_url: str = Field(description="The endpoint URL of the S3 bucket")
    vaultops_s3_access_key: str = Field(description="The access key for the S3 bucket")
    vaultops_s3_secret_key: str = Field(description="The secret key for the S3 bucket")
    vaultops_s3_signature_version: str = Field(description="The signature version for the S3 bucket")
    vaultops_s3_region: str = Field(description="The region of the S3 bucket")

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
                signature_version=self.vaultops_s3_signature_version,
                retries={"max_attempts": 3, "mode": "standard"},
            ),
            verify=True,
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
        except ClientError as e:
            if (not error_on_missing_file) and e.response["Error"]["Code"] == "NoSuchKey":
                return None
            raise ValueError("S3 Client Error") from e
        except Exception as e:
            raise ValueError("Error reading file from S3") from e

    def add_to_ansible_inventory(self, inventory: InventoryData) -> None:
        """
        Add the Vault configuration to the Ansible inventory file.

        Args:
            inventory: The path to the Ansible inventory file.
        """
        inventory.set_variable(
            "all", "vaultops_s3_aes256_sse_customer_key_base64", self.vaultops_s3_aes256_sse_customer_key_base64
        )
        inventory.set_variable("all", "vaultops_s3_bucket_name", self.vaultops_s3_bucket_name)
        inventory.set_variable("all", "vaultops_s3_endpoint_url", self.vaultops_s3_endpoint_url)
        inventory.set_variable("all", "vaultops_s3_access_key", self.vaultops_s3_access_key)
        inventory.set_variable("all", "vaultops_s3_secret_key", self.vaultops_s3_secret_key)
        inventory.set_variable("all", "vaultops_s3_signature_version", self.vaultops_s3_signature_version)
        inventory.set_variable("all", "vaultops_s3_region", self.vaultops_s3_region)


def get_storage_config(bws_id: str) -> StorageConfig:
    """

    Returns:

    """
    __bitwarden_client: BitwardenClient = BitwardenClient(
        client_settings_from_dict(
            {
                "apiUrl": os.getenv("API_URL", "https://api.bitwarden.com"),
                "deviceType": DeviceType.SDK,
                "identityUrl": os.getenv("IDENTITY_URL", "https://identity.bitwarden.com"),
                "userAgent": "Python",
            }
        )
    )
    __bitwarden_client.access_token_login(os.environ["BWS_ACCESS_TOKEN"])
    secrets_value_json = __bitwarden_client.secrets().get(bws_id).data.value
    return StorageConfig(**json.loads(secrets_value_json))
