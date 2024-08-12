import dataclasses
from typing import Dict, List, Optional

from cryptography.x509 import Certificate, NameOID
from cryptography.x509.oid import ExtendedKeyUsageOID
from pydantic import BaseModel, Field


@dataclasses.dataclass
class GeneratedCertificate:
    """
    Represents a generated certificate.

    Attributes:
        certificate (Certificate): The certificate object.
        certificate_content (str): The content of the certificate.
        need_to_generate (bool): Indicates whether the certificate needs to be generated.
        certificate_full_chain (Optional[str]): The full chain of the certificate (optional).
        need_to_generate_reason (Optional[str]): The reason for generating the certificate (optional).
    """

    certificate: Certificate
    certificate_content: str
    need_to_generate: bool
    certificate_full_chain: Optional[str]
    need_to_generate_reason: Optional[str]


class CertificateDetailsKeyUsage(BaseModel):
    """
    Represents the key usage details of a certificate.

    Attributes:
        digital_signature (bool): Set digital signature of the certificate.
        content_commitment (bool): Set content commitment of the certificate.
        key_encipherment (bool): Set key encipherment of the certificate.
        data_encipherment (bool): Set data encipherment of the certificate.
        key_agreement (bool): Set key agreement of the certificate.
        key_cert_sign (bool): Set key cert sign of the certificate.
        crl_sign (bool): Set crl sign of the certificate.
        encipher_only (bool): Set encipher only of the certificate.
        decipher_only (bool): Set decipher only of the certificate.
    """

    digital_signature: bool = Field(False, description="Set digital signature of the certificate")
    content_commitment: bool = Field(False, description="Set content commitment of the certificate")
    key_encipherment: bool = Field(False, description="Set key encipherment of the certificate")
    data_encipherment: bool = Field(False, description="Set data encipherment of the certificate")
    key_agreement: bool = Field(False, description="Set key agreement of the certificate")
    key_cert_sign: bool = Field(False, description="Set key cert sign of the certificate")
    crl_sign: bool = Field(False, description="Set crl sign of the certificate")
    encipher_only: bool = Field(False, description="Set encipher only of the certificate")
    decipher_only: bool = Field(False, description="Set decipher only of the certificate")


class CertificateDetailsBasicConstraints(BaseModel):
    """
    Represents the basic constraints of a certificate.

    Attributes:
        ca (bool): Indicates if the certificate is a CA (Certificate Authority).
        path_length (Optional[int]): The maximum number of intermediate CAs that can follow this certificate.
    """

    ca: bool = Field(False, description="Set ca of the certificate")
    path_length: Optional[int] = Field(None, description="Set path length of the certificate")


class CertificateDetails(BaseModel):
    """
    Represents the details of a certificate.

    Attributes:
        name (Dict[str, str]): Name of the certificate.
        set_public_key (bool): Flag indicating whether to set the public key of the certificate.
        authority_key_identifier (bool): Flag indicating whether to set the authority key identifier of the certificate.
        authority_key_identifier_critical (bool): Flag indicating whether the authority key identifier is critical.
        subject_key_identifier (bool): Flag indicating whether to set the subject key identifier of the certificate.
        subject_key_identifier_critical (bool): Flag indicating whether the subject key identifier is critical.
        key_usage (CertificateDetailsKeyUsage): Key usage of the certificate.
        key_usage_critical (bool): Flag indicating whether the key usage is critical.
        extended_key_usage (List[str]): Extended key usage of the certificate.
        extended_key_usage_critical (bool): Flag indicating whether the extended key usage is critical.
        basic_constraints (CertificateDetailsBasicConstraints): Basic constraints of the certificate.
        basic_constraints_critical (bool): Flag indicating whether the basic constraints are critical.
        subject_alternative_name (List[str]): Subject alternative name of the certificate.
        subject_alternative_name_critical (bool): Flag indicating whether the subject alternative name is critical.
        not_valid_after (int): Number of days after which the certificate is not valid.
    """

    name: Dict[str, str] = Field(
        ...,
        description="Name of the certificate, available options: "
        + ", ".join([f for f in dir(NameOID) if not callable(getattr(NameOID, f)) and not f.startswith("__")]),
    )

    set_public_key: bool = Field(default=True, description="Set public key of the certificate")
    authority_key_identifier: bool = Field(default=False, description="Set authority key identifier of the certificate")
    authority_key_identifier_critical: bool = Field(default=False, description="Set authority key identifier critical")
    subject_key_identifier: bool = Field(default=False, description="Set subject key identifier of the certificate")
    subject_key_identifier_critical: bool = Field(default=False, description="Set subject key identifier critical")
    key_usage: CertificateDetailsKeyUsage = Field(default=None, description="Set key usage of the certificate")
    key_usage_critical: bool = Field(default=False, description="Set key usage critical")
    extended_key_usage: List[str] = Field(
        default=None,
        description="Set extended key usage of the certificate, available options: "
        + ", ".join(
            [
                f
                for f in dir(ExtendedKeyUsageOID)
                if not callable(getattr(ExtendedKeyUsageOID, f)) and not f.startswith("__")
            ]
        ),
    )
    extended_key_usage_critical: bool = Field(default=False, description="Set extended key usage critical")
    basic_constraints: CertificateDetailsBasicConstraints = Field(
        None, description="Set basic constraints of the certificate"
    )
    basic_constraints_critical: bool = Field(default=False, description="Set basic constraints critical")
    subject_alternative_name: List[str] = Field(
        default=None,
        description="Set subject alternative name of the certificate, "
        "example: DNS:example.com, URI:https://example.com, IP:127.0.0.1",
    )
    subject_alternative_name_critical: bool = Field(default=False, description="Set subject alternative name critical")
    not_valid_after: int = Field(default=30, description="Set not valid after days of the certificate")


class CertificateProperties(BaseModel):
    """
    Represents the properties of a certificate.

    Attributes:
        certificate_content (Optional[str]): Content of the certificate.
        certificate_details (CertificateDetails): Details of the certificate.
    """

    certificate_content: Optional[str] = Field(default=None, description="Content of the certificate")
    certificate_details: CertificateDetails = Field(..., description="Details of the certificate")
