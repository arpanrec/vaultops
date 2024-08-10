#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module provides functionality for handling private keys
in the context of HashiCorp Vault initialization and unsealing.

It defines the following classes:
- PrivateKeyProperties: Represents the properties of a private key.
- GeneratedPrivateKey: Represents a generated private key.

And the following function:
- generate_private_key: Handles operations related to private keys.

The module also imports the following modules:
- dataclasses
- os
- pathlib
- typing
- cryptography.hazmat.backends
- cryptography.hazmat.primitives
- cryptography.hazmat.primitives.asymmetric.rsa
- cryptography.hazmat.primitives.asymmetric.types
- cryptography.hazmat.primitives.asymmetric
- pydantic
- VaultOpsRetryError (imported from the parent package)

Note: This module requires the cryptography and pydantic libraries to be installed.
"""

import os
import pathlib
from typing import Any, Optional

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes

from .. import VaultOpsRetryError
from ..models.pki_private_key import GeneratedPrivateKey, PrivateKeyProperties


# pylint: disable=too-many-locals
def generate_private_key(private_key_properties: PrivateKeyProperties) -> GeneratedPrivateKey:
    """
    Handles operations related to private keys.

    Parameters:
    private_key_properties (PrivateKeyProperties): Properties for the private key.

    Returns:
    Dict: A Dict containing the private key, a literal string, a boolean value, and another literal string.
    """

    private_key_path: Optional[str] = None
    private_key_content: Optional[str] = private_key_properties.private_key_content
    private_key_passphrase: Optional[str] = private_key_properties.private_key_passphrase
    public_exponent: int = private_key_properties.public_exponent
    key_size: int = private_key_properties.key_size
    private_key_file_mode: int = 0o600

    __private_key_backend: Any = default_backend()

    if private_key_path and private_key_content:
        raise VaultOpsRetryError("Only one of private_key_path or private_key_content can be specified")

    if private_key_path and os.path.exists(private_key_path) and pathlib.Path(private_key_path).is_dir():
        raise VaultOpsRetryError(f"private_key_path '{private_key_path}' is a directory, not a file")

    rsa_private_key: Optional[PrivateKeyTypes] = None
    need_to_generate: bool = False
    need_to_generate_reason: Optional[str] = None
    encryption_algorithm_private_key = (
        serialization.BestAvailableEncryption(private_key_passphrase.encode(encoding="utf-8", errors="strict"))
        if private_key_passphrase
        else serialization.NoEncryption()
    )

    if private_key_path and os.path.exists(private_key_path) and pathlib.Path(private_key_path).is_file():
        with open(private_key_path, "r", encoding="utf-8") as f:
            private_key_content = f.read()
    elif private_key_path and (not os.path.exists(private_key_path) or not pathlib.Path(private_key_path).is_file()):
        need_to_generate = True
        need_to_generate_reason = "private_key_path does not exist"

    if private_key_content:
        try:
            rsa_private_key = serialization.load_pem_private_key(
                private_key_content.encode(encoding="utf-8", errors="strict"),
                password=(
                    private_key_passphrase.encode(encoding="utf-8", errors="strict") if private_key_passphrase else None
                ),
                backend=__private_key_backend,
            )
        except Exception as e:  # pylint: disable=broad-except
            need_to_generate = True
            need_to_generate_reason = "private_key_content is invalid + " + str(e)
    else:
        need_to_generate = True
        need_to_generate_reason = "private_key_content is empty"

    if not need_to_generate and rsa_private_key.key_size != key_size:  # type: ignore
        need_to_generate = True
        need_to_generate_reason = "key_size is not valid"

    if not need_to_generate and rsa_private_key.public_key().public_numbers().e != public_exponent:  # type: ignore
        need_to_generate = True
        need_to_generate_reason = "public_exponent is not valid"

    if need_to_generate:
        rsa_private_key = rsa.generate_private_key(
            public_exponent=public_exponent,
            key_size=key_size,
            backend=__private_key_backend,
        )

    private_key_bytes: bytes = rsa_private_key.private_bytes(  # type: ignore
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=encryption_algorithm_private_key,
    )

    if private_key_path:
        # Remove existing file if it exists
        if os.path.exists(private_key_path):
            os.remove(private_key_path)
        with open(private_key_path, "wb") as f:
            f.write(private_key_bytes)
        os.chmod(private_key_path, private_key_file_mode)

    generated_private_key: GeneratedPrivateKey = GeneratedPrivateKey(
        private_key=rsa_private_key,  # type: ignore
        private_key_content=private_key_bytes.decode("utf-8"),
        private_key_passphrase=private_key_passphrase,
        need_to_generate=need_to_generate,
        need_to_generate_reason=need_to_generate_reason,
    )

    return generated_private_key
