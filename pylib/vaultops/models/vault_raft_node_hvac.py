import os
from typing import Optional

import hvac  # type: ignore
import requests
from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes
from cryptography.x509 import Certificate
from pydantic import ConfigDict, Field, computed_field
from requests.sessions import HTTPAdapter
from urllib3 import Retry

from ..vault_setup.certificate import generate_x590_certificate
from ..vault_setup.private_key import generate_private_key
from .certificate import (
    CertificateDetails,
    CertificateDetailsBasicConstraints,
    CertificateDetailsKeyUsage,
    CertificateProperties,
    GeneratedCertificate,
)
from .pki_private_key import GeneratedPrivateKey, PrivateKeyProperties
from .vault_raft_node import VaultRaftNode


class VaultRaftNodeHvac(VaultRaftNode):
    """
    Represents a Vault Raft node with HVAC client configuration.

    Attributes:
        model_config (ConfigDict): The model configuration.
        vault_root_ca_cert_file (str): The path to the file containing the root CA certificate.
        _vault_client (Optional[hvac.Client]): The HVAC client instance.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    _vault_client: Optional[hvac.Client] = None
    vault_root_ca_cert_file: str = Field(
        default=..., description="The path to the file containing the root CA certificate."
    )

    def __init__(self, rsa_root_ca_key: PrivateKeyTypes, rsa_root_ca_cert: Certificate, **data):
        super().__init__(**data)
        generated_vault_client_private_key: GeneratedPrivateKey = generate_private_key(PrivateKeyProperties())
        with open(self.client_key_path, "w", encoding="utf-8") as f:
            f.write(generated_vault_client_private_key.private_key_content)

        generated_vault_client_certificate: GeneratedCertificate = generate_x590_certificate(
            rsa_private_key=generated_vault_client_private_key.private_key,
            certificate_authority=(rsa_root_ca_cert, rsa_root_ca_key),
            certificate_properties=CertificateProperties(
                certificate_details=CertificateDetails(
                    name={"COMMON_NAME": self.node_id},
                    # pylint: disable=R0801
                    key_usage=CertificateDetailsKeyUsage(
                        digital_signature=True,
                        content_commitment=True,
                        key_encipherment=True,
                        data_encipherment=False,
                        key_agreement=False,
                        key_cert_sign=False,
                        crl_sign=False,
                        encipher_only=False,
                        decipher_only=False,
                    ),
                    key_usage_critical=True,
                    basic_constraints=CertificateDetailsBasicConstraints(ca=False, path_length=None),
                    subject_alternative_name=self.subject_alt_name,
                    not_valid_after=90,
                    extended_key_usage=["CLIENT_AUTH"],
                    extended_key_usage_critical=True,
                )
            ),
        )

        with open(self.client_cert_path, "w", encoding="utf-8") as f:
            f.write(str(generated_vault_client_certificate.certificate_full_chain))

    @computed_field(return_type=str)  # type: ignore
    @property
    def client_cert_path(self) -> str:
        """
        Returns the path to the client certificate file.
        Returns:
            str: The path to the client certificate file.
        """
        return os.path.join(self.vaultops_raft_node_tmp_dir_path, "vault-client-cert.pem")

    @computed_field(return_type=str)  # type: ignore
    @property
    def client_key_path(self) -> str:
        """
        Returns the path to the client private key file.
        Returns:
            str: The path to the client private key file.
        """
        return os.path.join(self.vaultops_raft_node_tmp_dir_path, "vault-client-priv.key")

    @computed_field(return_type=hvac.Client)  # type: ignore
    @property
    def hvac_client(self) -> hvac.Client:
        """
        Returns the HVAC client instance.

        If the client instance is already created, it returns the existing instance.
        Otherwise, it creates a new instance and returns it.

        Returns:
            hvac.Client: The HVAC client instance.
        """

        if not self._vault_client:
            adapter = HTTPAdapter(max_retries=Retry(total=2, backoff_factor=2))
            session = requests.Session()
            session.verify = self.vault_root_ca_cert_file
            session.cert = (self.client_cert_path, self.client_key_path)
            session.mount("https://", adapter)
            hvac_client = hvac.Client(url=self.api_addr, session=session)
            self._vault_client = hvac_client

        return self._vault_client
