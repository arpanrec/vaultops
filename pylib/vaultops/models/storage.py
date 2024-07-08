import os
from typing import Any

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
        description="BWS ID: The base64-encoded AES256 key for the S3 bucket")
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
