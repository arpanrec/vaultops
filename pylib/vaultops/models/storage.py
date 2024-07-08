import base64
import os
from typing import Any, Optional

import boto3
from ansible.inventory.data import InventoryData  # type: ignore
from botocore.config import Config
from botocore.exceptions import ClientError
from botocore.response import StreamingBody
from mypy_boto3_s3.type_defs import GetObjectOutputTypeDef
from pydantic import Field, BaseModel, computed_field
from bitwarden_sdk import BitwardenClient, DeviceType, client_settings_from_dict  # type: ignore


class StorageConfig(BaseModel):
    """
    Represents the secrets required for interacting with HashiCorp Vault.

    Attributes:
        vaultops_s3_aes256_sse_customer_key_base64_bws_id (str):
            - BWS ID: The base64-encoded AES256 key for the S3 bucket.
        vaultops_s3_bucket_name_bws_id (str): BWS ID: The name of the S3 bucket.
        vaultops_s3_endpoint_url_bws_id (str): BWS ID: The endpoint URL of the S3 bucket.
        vaultops_s3_access_key_bws_id (str): BWS ID: The access key for the S3 bucket.
        vaultops_s3_secret_key_bws_id (str): BWS ID: The secret key for the S3 bucket.
        vaultops_s3_signature_version_bws_id BWS ID: (str): The signature version for the S3 bucket.
        vaultops_s3_region_bws_id (str): BWS ID: The region of the S3 bucket.
    """

    vaultops_s3_aes256_sse_customer_key_base64_bws_id: str = Field(
        description="BWS ID: The base64-encoded AES256 key for the S3 bucket"
    )
    vaultops_s3_bucket_name_bws_id: str = Field(description="BWS ID: The name of the S3 bucket")
    vaultops_s3_endpoint_url_bws_id: str = Field(description="BWS ID: The endpoint URL of the S3 bucket")
    vaultops_s3_access_key_bws_id: str = Field(description="BWS ID: The access key for the S3 bucket")
    vaultops_s3_secret_key_bws_id: str = Field(description="BWS ID: The secret key for the S3 bucket")
    vaultops_s3_signature_version_bws_id: str = Field(description="BWS ID: The signature version for the S3 bucket")
    vaultops_s3_region_bws_id: str = Field(description="BWS ID: The region of the S3 bucket")

    __bitwarden_client: BitwardenClient

    def __init__(self, **data: Any):
        super().__init__(**data)

        self.__bitwarden_client = BitwardenClient(
            client_settings_from_dict(
                {
                    "apiUrl": os.getenv("API_URL", "https://api.bitwarden.com"),
                    "deviceType": DeviceType.SDK,
                    "identityUrl": os.getenv("IDENTITY_URL", "https://identity.bitwarden.com"),
                    "userAgent": "Python",
                }
            )
        )
        self.__bitwarden_client.access_token_login(os.environ["BWS_ACCESS_TOKEN"])

    @computed_field(return_type=str)  # type: ignore
    @property
    def vaultops_s3_aes256_sse_customer_key_base64(self) -> str:
        """
        Returns the AES256 key for the S3 bucket.

        Returns:
            str: The AES256 key for the S3 bucket.
        """

        return self.__bitwarden_client.secrets().get(self.vaultops_s3_aes256_sse_customer_key_base64_bws_id).data.value

    @computed_field(return_type=str)  # type: ignore
    @property
    def vaultops_s3_bucket_name(self) -> str:
        """
        Returns the name of the S3 bucket.

        Returns:
            str: The name of the S3 bucket.
        """

        return self.__bitwarden_client.secrets().get(self.vaultops_s3_bucket_name_bws_id).data.value

    @computed_field(return_type=str)  # type: ignore
    @property
    def vaultops_s3_endpoint_url(self) -> str:
        """
        Returns the endpoint URL of the S3 bucket.

        Returns:
            str: The endpoint URL of the S3 bucket.
        """

        return self.__bitwarden_client.secrets().get(self.vaultops_s3_endpoint_url_bws_id).data.value

    @computed_field(return_type=str)  # type: ignore
    @property
    def vaultops_s3_access_key(self) -> str:
        """
        Returns the access key for the S3 bucket.

        Returns:
            str: The access key for the S3 bucket.
        """

        return self.__bitwarden_client.secrets().get(self.vaultops_s3_access_key_bws_id).data.value

    @computed_field(return_type=str)  # type: ignore
    @property
    def vaultops_s3_secret_key(self) -> str:
        """
        Returns the secret key for the S3 bucket.

        Returns:
            str: The secret key for the S3 bucket.
        """

        return self.__bitwarden_client.secrets().get(self.vaultops_s3_secret_key_bws_id).data.value

    @computed_field(return_type=str)  # type: ignore
    @property
    def vaultops_s3_signature_version(self) -> str:
        """
        Returns the signature version for the S3 bucket.

        Returns:
            str: The signature version for the S3 bucket.
        """

        return self.__bitwarden_client.secrets().get(self.vaultops_s3_signature_version_bws_id).data.value

    @computed_field(return_type=str)  # type: ignore
    @property
    def vaultops_s3_region(self) -> str:
        """
        Returns the region of the S3 bucket.

        Returns:
            str: The region of the S3 bucket.
        """

        return self.__bitwarden_client.secrets().get(self.vaultops_s3_region_bws_id).data.value

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
