from pydantic import Field, BaseModel


class BackendConfig(BaseModel):
    """
    Represents the secrets required for interacting with HashiCorp Vault.

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

    vaultops_s3_aes256_sse_customer_key_base64: str
    vaultops_s3_bucket_name: str
    vaultops_s3_endpoint_url: str
    vaultops_s3_access_key: str
    vaultops_s3_secret_key: str
    vaultops_s3_signature_version: str = Field(default="s3v4", description="The signature version for the S3 bucket")
    vaultops_s3_region: str = Field(description="The region of the S3 bucket")
