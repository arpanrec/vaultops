from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class VaultNewRootToken(BaseModel):
    """
    Represents the response for generating a new root token in HashiCorp Vault.

    Attributes:
        otp (str): The one-time password used for generating the root token.
        generate_root_response (Dict[str, Any]):
            - The response received from the Vault API when generating the root token.
        encoded_root_token (str): The encoded value of the new root token.
        new_root (Optional[str]): The new root token value, if generated successfully. Defaults to None.
    """

    otp: str
    generate_root_response: Dict[str, Any]
    encoded_root_token: str
    new_root: Optional[str] = Field(default=None)
