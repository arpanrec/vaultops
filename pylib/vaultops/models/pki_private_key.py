import dataclasses
from typing import Optional

from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from pydantic import BaseModel, Field


class PrivateKeyProperties(BaseModel):
    """
    Represents the properties of a private key.

    Attributes:
        private_key_content (Optional[str]): Content of the private key.
        private_key_passphrase (Optional[str]): Passphrase for the private key.
        public_exponent (int): Public exponent for the RSA key.
        key_size (int): Size of the key.
    """

    private_key_content: Optional[str] = Field(default=None, description="Content of the private key")
    private_key_passphrase: Optional[str] = Field(default=None, description="Passphrase for the private key")
    public_exponent: int = Field(default=65537, description="Public exponent for the RSA key")
    key_size: int = Field(default=2048, description="Size of the key")


@dataclasses.dataclass
class GeneratedPrivateKey:
    """
    Represents a generated private key.

    Attributes:
        private_key: The RSA private key object.
        private_key_content: The content of the private key.
        private_key_passphrase: The passphrase for the private key (optional).
        need_to_generate: Indicates whether a new private key needs to be generated.
        need_to_generate_reason: The reason for generating a new private key (optional).
    """

    private_key: RSAPrivateKey
    private_key_content: str
    private_key_passphrase: Optional[str]
    need_to_generate: bool
    need_to_generate_reason: Optional[str]
