#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module provides functionality for working with X.509 certificates.

The module includes classes and functions for generating, loading, and manipulating X.509 certificates.

It also provides a set of data classes that represent different aspects of a certificate,
such as key usage, basic constraints, and certificate details.

Classes:
- CertificateDetailsKeyUsage: Represents the key usage details of a certificate.
- CertificateDetailsBasicConstraints: Represents the basic constraints of a certificate.
- CertificateDetails: Represents the details of a certificate.
- CertificateProperties: Represents the properties of a certificate.
- GeneratedCertificate: Represents a generated certificate.

Functions:
- _is_property_set(properties: Dict[str, Any], property_name: str) -> bool: Checks if a property is set.
- _load_existing_certificate(
    certificate_path: Optional[str] = None,
    certificate_content: Optional[str] = None
    ) -> Tuple[Optional[Certificate], Optional[str]]: Handles loading an existing certificate.
- generate_x590_certificate(
    rsa_private_key: PrivateKeyTypes,
    certificate_properties: CertificateProperties,
    certificate_authority: Optional[Tuple[Certificate, PrivateKeyTypes]] = None
    ) -> GeneratedCertificate: Handles operations related to X.590 certificates.

Note: This module requires the cryptography and pydantic libraries to be installed.
"""

import datetime
import os
import pathlib
from ipaddress import IPv4Address, IPv6Address
from typing import Any, Dict, List, Optional, Tuple

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.types import CertificatePublicKeyTypes, PrivateKeyTypes
from cryptography.x509 import (
    AuthorityKeyIdentifier,
    BasicConstraints,
    Certificate,
    CertificateBuilder,
    DNSName,
    ExtendedKeyUsage,
    Extension,
    ExtensionNotFound,
    GeneralName,
    IPAddress,
    KeyUsage,
    Name,
    NameAttribute,
    NameOID,
    RFC822Name,
    SubjectAlternativeName,
    SubjectKeyIdentifier,
    UniformResourceIdentifier,
    load_pem_x509_certificate,
    random_serial_number,
)
from cryptography.x509.oid import ExtendedKeyUsageOID

from .. import VaultOpsRetryError
from ..models.certificate import CertificateDetails, CertificateProperties, GeneratedCertificate


def _is_property_set(properties: Dict[str, Any], property_name: str) -> bool:
    """
    Checks if a property is set.

    Parameters:
    properties (dict): A dictionary containing the properties.
    property_name (str): The name of the property to check.

    Returns:
    bool: True if the property is set, False otherwise.
    """

    return property_name in properties and properties[property_name] is not None


def _load_existing_certificate(
    certificate_path: Optional[str] = None, certificate_content: Optional[str] = None
) -> Tuple[Optional[Certificate], Optional[str]]:
    """
    Handles loading an existing certificate.

    Parameters:
    certificate_path (str, optional): Path to the certificate file.
    certificate_content (str, optional): Content of the certificate.

    Returns:
    Certificate: The loaded certificate.
    String: An exception if the certificate could not be loaded.
    """

    if certificate_path and certificate_content:
        raise VaultOpsRetryError("Only one of certificate_path or certificate_content can be specified")

    if certificate_path and os.path.exists(certificate_path) and pathlib.Path(certificate_path).is_dir():
        raise VaultOpsRetryError(f"certificate_path '{certificate_path}' is a directory, not a file")

    _x590_certificate: Optional[Certificate] = None

    if certificate_path and os.path.exists(certificate_path) and pathlib.Path(certificate_path).is_file():
        with open(certificate_path, "r", encoding="utf-8") as f:
            certificate_content = f.read()
    elif certificate_path and (not os.path.exists(certificate_path) or not pathlib.Path(certificate_path).is_file()):
        return None, "certificate_path does not exist"

    if certificate_content:
        try:
            _x590_certificate = load_pem_x509_certificate(
                certificate_content.encode(encoding="utf-8", errors="strict"),
                default_backend(),
            )
        except Exception as e:  # pylint: disable=broad-except
            return None, "certificate_content is invalid + " + str(e)
    else:
        return None, "certificate_content is empty"

    return _x590_certificate, None


# pylint: disable=R0913,R0914,R0912,R0915
def generate_x590_certificate(
    rsa_private_key: PrivateKeyTypes,
    certificate_properties: CertificateProperties,
    certificate_authority: Optional[Tuple[Certificate, PrivateKeyTypes]] = None,
) -> GeneratedCertificate:
    """
    Handles operations related to X.590 certificates.

    Parameters:
        rsa_private_key (PrivateKeyTypes): The private key to use for signing the certificate.
        certificate_authority (Optional[Tuple[Certificate, PrivateKeyTypes]]):
            - The certificate authority to use for signing the certificate.
        certificate_properties (CertificateProperties): Properties for the certificate.

    Returns:
        GeneratedCertificate:
            - A GeneratedCertificate object containing the generated certificate, a boolean value, and a string.
    """

    certificate_path: Optional[str] = None
    certificate_content: Optional[str] = certificate_properties.certificate_content
    properties: CertificateDetails = certificate_properties.certificate_details
    certificate_file_mode: int = 0o444

    if certificate_path and certificate_content:
        raise VaultOpsRetryError("Only one of certificate_path or certificate_content can be specified")

    if certificate_path and os.path.exists(certificate_path) and pathlib.Path(certificate_path).is_dir():
        raise VaultOpsRetryError(f"certificate_path '{certificate_path}' is a directory, not a file")

    if not rsa_private_key:
        raise VaultOpsRetryError("rsa_private_key is required")

    need_to_generate: bool = False
    need_to_generate_reason: Optional[str] = None
    _x590_certificate: Certificate
    # Check if certificate is there and set _x590_certificate
    certificate_load_exception: Tuple[Optional[Certificate], Optional[str]] = _load_existing_certificate(
        certificate_path=certificate_path, certificate_content=certificate_content
    )
    if certificate_load_exception[1]:
        need_to_generate = True
        need_to_generate_reason = certificate_load_exception[1]
    else:
        _x590_certificate = certificate_load_exception[0]  # type: ignore

    builder = CertificateBuilder()
    expected_serial_number: int = random_serial_number()
    builder = builder.serial_number(expected_serial_number)

    # Set Expectation for the certificate -----------------------------------------------------------------------------

    # Subject Name
    if not properties.name and not certificate_authority:
        raise VaultOpsRetryError("NAME is required")

    if properties.name:
        expected_subject_name = Name(
            [NameAttribute(getattr(NameOID, name_key), name_value) for name_key, name_value in properties.name.items()]
        )
    else:
        expected_subject_name = certificate_authority[0].subject  # type: ignore

    builder = builder.subject_name(expected_subject_name)

    # Issuer Name
    if certificate_authority:
        expected_issuer_name = certificate_authority[0].subject
    else:
        expected_issuer_name = expected_subject_name

    builder = builder.issuer_name(expected_issuer_name)

    # Public Key
    expected_public_key: Optional[CertificatePublicKeyTypes] = None
    if properties.set_public_key:
        expected_public_key = rsa_private_key.public_key()  # type: ignore

    if expected_public_key:
        builder = builder.public_key(expected_public_key)

    # Authority Key Identifier
    expected_authority_key_identifier_value: Optional[AuthorityKeyIdentifier] = None
    expected_authority_key_identifier_critical: Optional[bool] = None

    if not properties.authority_key_identifier and properties.authority_key_identifier_critical:
        raise VaultOpsRetryError(
            "authority_key_identifier_critical cannot be set without authority_key_identifier to True"
        )

    if properties.authority_key_identifier and certificate_authority:
        issuer_general_names: SubjectAlternativeName = SubjectAlternativeName([])

        try:
            issuer_general_names = (
                certificate_authority[0].extensions.get_extension_for_class(SubjectAlternativeName).value
            )
        except ExtensionNotFound:
            pass
        except Exception as e:
            raise VaultOpsRetryError("Something went wrong") from e

        expected_authority_key_identifier_value = AuthorityKeyIdentifier(
            key_identifier=AuthorityKeyIdentifier.from_issuer_public_key(
                certificate_authority[0].public_key()  # type: ignore
            ).key_identifier,
            authority_cert_serial_number=certificate_authority[0].serial_number,
            authority_cert_issuer=issuer_general_names,
        )
    elif properties.authority_key_identifier:
        raise VaultOpsRetryError("authority_key_identifier cannot be set without certificate_authority")

    if expected_authority_key_identifier_value:
        expected_authority_key_identifier_critical = properties.authority_key_identifier_critical
        builder = builder.add_extension(
            expected_authority_key_identifier_value,
            critical=expected_authority_key_identifier_critical,
        )

    # Subject Key Identifier
    expected_subject_key_identifier_value: Optional[SubjectKeyIdentifier] = None
    expected_subject_key_identifier_critical: Optional[bool] = None
    if properties.subject_key_identifier:
        expected_subject_key_identifier_value = SubjectKeyIdentifier.from_public_key(
            rsa_private_key.public_key()  # type: ignore
        )

    if not expected_subject_key_identifier_value and properties.subject_key_identifier_critical:
        raise VaultOpsRetryError(
            "SetSubjectKeyIdentifierCritical cannot be set without SetSubjectKeyIdentifier to True"
        )

    if expected_subject_key_identifier_value:
        expected_subject_key_identifier_critical = properties.subject_key_identifier_critical
        builder = builder.add_extension(
            expected_subject_key_identifier_value,
            critical=expected_subject_key_identifier_critical,
        )

    # Key Usage
    expected_key_usage_value: Optional[KeyUsage] = None
    expected_key_usage_critical: Optional[bool] = None
    if properties.key_usage:
        expected_key_usage_value = KeyUsage(**properties.key_usage.model_dump())

    if not expected_key_usage_value and properties.key_usage_critical:
        raise VaultOpsRetryError("key_usage_critical cannot be set without key_usage")

    if expected_key_usage_value:
        expected_key_usage_critical = properties.key_usage_critical or False
        builder = builder.add_extension(expected_key_usage_value, critical=expected_key_usage_critical)

    # Extended Key Usage
    expected_extended_key_usage_value: Optional[ExtendedKeyUsage] = None
    expected_extended_key_usage_critical: Optional[bool] = None

    if properties.extended_key_usage:
        expected_extended_key_usage_value = ExtendedKeyUsage(
            [
                ExtendedKeyUsageOID.__getattribute__(ExtendedKeyUsageOID, usage)
                for usage in properties.extended_key_usage or []
            ]
        )

    if not expected_extended_key_usage_value and properties.extended_key_usage_critical:
        raise VaultOpsRetryError("extended_key_usage_critical cannot be set without extended_key_usage")

    if expected_extended_key_usage_value:
        expected_extended_key_usage_critical = properties.extended_key_usage_critical or False
        builder = builder.add_extension(
            expected_extended_key_usage_value,
            critical=expected_extended_key_usage_critical,
        )

    # Basic Constraints
    expected_basic_constraints_value: Optional[BasicConstraints] = None
    expected_basic_constraints_critical: Optional[bool] = None  # properties.get("BasicConstraintsCritical", False)

    if properties.basic_constraints:
        expected_basic_constraints_value = BasicConstraints(
            ca=properties.basic_constraints.ca,
            path_length=properties.basic_constraints.path_length,
        )
    if not expected_basic_constraints_value and properties.basic_constraints_critical:
        raise VaultOpsRetryError("basic_constraints_critical cannot be set without basic_constraints")

    if expected_basic_constraints_value:
        expected_basic_constraints_critical = properties.basic_constraints_critical or False
        builder = builder.add_extension(
            expected_basic_constraints_value,
            critical=expected_basic_constraints_critical,
        )

    # Subject Alternative Name
    expected_subject_alternative_name_value: Optional[SubjectAlternativeName] = None
    expected_subject_alternative_name_critical: Optional[bool] = (
        None  # properties.get("SubjectAlternativeNameCritical", False)
    )

    if properties.subject_alternative_name:
        expected_san_entries: List[GeneralName] = []
        for san in properties.subject_alternative_name:
            if san.startswith("DNS:"):
                expected_san_entries.append(DNSName(san[4:]))
            elif san.startswith("URI:"):
                expected_san_entries.append(UniformResourceIdentifier(san[4:]))
            elif san.startswith("IP:"):
                ip = san[3:]
                if ":" in ip:
                    expected_san_entries.append(IPAddress(IPv6Address(ip)))
                else:
                    expected_san_entries.append(IPAddress(IPv4Address(ip)))
            elif san.startswith("EMAIL:"):
                expected_san_entries.append(RFC822Name(san[6:]))
            else:
                raise VaultOpsRetryError(
                    f"Unknown subject_alternative_name type: {san}. Supported types are: DNS, URI, IP, EMAIL"
                )

        expected_subject_alternative_name_value = SubjectAlternativeName(expected_san_entries)

    if not expected_subject_alternative_name_value and properties.subject_alternative_name_critical:
        raise VaultOpsRetryError("subject_alternative_name_critical cannot be set without subject_alternative_name")

    if expected_subject_alternative_name_value:
        expected_subject_alternative_name_critical = properties.subject_alternative_name_critical or False
        builder = builder.add_extension(
            expected_subject_alternative_name_value,
            critical=expected_subject_alternative_name_critical,
        )

    # Validity
    if not properties.not_valid_after:
        raise VaultOpsRetryError("not_valid_after is required")

    now = datetime.datetime.now(datetime.timezone.utc)
    expected_not_valid_before = now
    expected_not_valid_after = now + datetime.timedelta(days=int(properties.not_valid_after))

    # Check if Expected Valid after is less than CA Valid Till
    if certificate_authority:
        certificate_authority_certificate: Certificate = certificate_authority[0]
        issuer_valid_till: datetime.datetime = certificate_authority_certificate.not_valid_after_utc

        if expected_not_valid_after > issuer_valid_till:
            raise VaultOpsRetryError("Certificate Authority is not valid for the duration of the certificate")

    builder = builder.not_valid_before(expected_not_valid_before)
    builder = builder.not_valid_after(expected_not_valid_after)

    # If certificate_authority is set, then sign the certificate with the certificate_authority's private key
    if certificate_authority:
        certificate_authority_private_key: PrivateKeyTypes = certificate_authority[1]
    else:
        certificate_authority_private_key = rsa_private_key

    # Validate the certificate ---------------------------------------------------------------------------------------

    # Subject Name
    if not need_to_generate and _x590_certificate and _x590_certificate.subject != expected_subject_name:
        need_to_generate = True
        need_to_generate_reason = (
            f"Existing certificate subject name is not as expected."
            f"Current: {_x590_certificate.subject} Expected: {expected_subject_name}"
        )

    # Issuer Name
    if not need_to_generate and _x590_certificate and _x590_certificate.issuer != expected_issuer_name:
        need_to_generate = True
        need_to_generate_reason = (
            f"Existing certificate issuer name is not as expected."
            f"Current: {_x590_certificate.issuer} Expected: {expected_issuer_name}"
        )

    # Public key
    if not need_to_generate and _x590_certificate and _x590_certificate.public_key() != expected_public_key:
        need_to_generate = True
        need_to_generate_reason = (
            f"Existing certificate's public key does not match private key used to sign it. "
            f"Current: {_x590_certificate.public_key()} Expected: {expected_public_key}."
        )

    # Authority Key Identifier
    if not need_to_generate:
        current_authority_key_identifier_value: Optional[AuthorityKeyIdentifier] = None
        current_authority_key_identifier_critical: Optional[bool] = None
        try:
            current_authority_key_identifier = _x590_certificate.extensions.get_extension_for_class(
                AuthorityKeyIdentifier
            )
            current_authority_key_identifier_value = current_authority_key_identifier.value
            current_authority_key_identifier_critical = current_authority_key_identifier.critical
        except ExtensionNotFound:
            pass
        except Exception as e:
            raise VaultOpsRetryError("Something went wrong") from e

        if current_authority_key_identifier_value != expected_authority_key_identifier_value:
            need_to_generate = True
            need_to_generate_reason = (
                f"Authority Key Identifier Mismatch, Existing Certificate is not signed by OwnCA."
                f"Current: {current_authority_key_identifier_value} Expected: {expected_authority_key_identifier_value}"
            )

        if (
            not need_to_generate
            and current_authority_key_identifier_critical != expected_authority_key_identifier_critical
        ):
            need_to_generate = True
            need_to_generate_reason = (
                f"Authority Key Identifier Critical Mismatch, Existing Certificate is not signed by OwnCA."
                f"Current: {current_authority_key_identifier_critical} "
                f"Expected: {expected_authority_key_identifier_critical}"
            )

    # Subject Key Identifier
    if not need_to_generate:
        current_subject_key_identifier_value: Optional[SubjectKeyIdentifier] = None
        current_subject_key_identifier_critical: Optional[bool] = None
        try:
            current_subject_key_identifier = _x590_certificate.extensions.get_extension_for_class(SubjectKeyIdentifier)
            current_subject_key_identifier_value = current_subject_key_identifier.value
            current_subject_key_identifier_critical = current_subject_key_identifier.critical or False
        except ExtensionNotFound:
            pass
        except Exception as e:
            raise VaultOpsRetryError("Something went wrong") from e

        if current_subject_key_identifier_value != expected_subject_key_identifier_value:
            need_to_generate = True
            need_to_generate_reason = (
                f"Subject Key Identifier Mismatch."
                f"Current: {current_subject_key_identifier_value} Expected: {expected_subject_key_identifier_value}"
            )

        if not need_to_generate and current_subject_key_identifier_critical != expected_subject_key_identifier_critical:
            need_to_generate = True
            need_to_generate_reason = (
                f"Subject Key Identifier Critical Mismatch."
                f"Current: {current_subject_key_identifier_critical} "
                f"Expected: {expected_subject_key_identifier_critical}"
            )

    # Key Usage
    if not need_to_generate:
        current_key_usage_value: Optional[KeyUsage] = None
        current_key_usage_critical: Optional[bool] = None
        try:
            current_key_usage: Extension[KeyUsage] = _x590_certificate.extensions.get_extension_for_class(KeyUsage)
            current_key_usage_value = current_key_usage.value
            current_key_usage_critical = current_key_usage.critical
        except ExtensionNotFound:
            pass
        except Exception as e:
            raise VaultOpsRetryError("Something went wrong") from e

        if expected_key_usage_value != current_key_usage_value:
            need_to_generate = True
            need_to_generate_reason = (
                f"Existing certificate's Key Usage does not match."
                f"Current: {current_key_usage_value} Expected: {expected_key_usage_value}"
            )

        if not need_to_generate and expected_key_usage_critical != current_key_usage_critical:
            need_to_generate = True
            need_to_generate_reason = (
                f"Existing certificate's Key Usage Critical does not match."
                f"Current: {current_key_usage_critical} Expected: {expected_key_usage_critical}"
            )

    # Extended Key Usage
    if not need_to_generate:
        current_extended_key_usage_value: Optional[ExtendedKeyUsage] = None
        current_extended_key_usage_critical: Optional[bool] = None

        try:
            current_extended_key_usage: Extension[ExtendedKeyUsage] = (
                _x590_certificate.extensions.get_extension_for_class(ExtendedKeyUsage)
            )
            current_extended_key_usage_value = current_extended_key_usage.value
            current_extended_key_usage_critical = current_extended_key_usage.critical
        except ExtensionNotFound:
            pass
        except Exception as e:
            raise VaultOpsRetryError("Something went wrong") from e

        if expected_extended_key_usage_value != current_extended_key_usage_value:
            need_to_generate = True
            need_to_generate_reason = (
                f"Existing certificate's Extended Key Usage does not match."
                f"Current: {current_extended_key_usage_value} Expected: {expected_extended_key_usage_value}"
            )

        if not need_to_generate and expected_extended_key_usage_critical != current_extended_key_usage_critical:
            need_to_generate = True
            need_to_generate_reason = (
                f"Existing certificate's Extended Key Usage Critical does not match."
                f"Current: {current_extended_key_usage_critical} Expected: {expected_extended_key_usage_critical}"
            )

    # Basic Constraints
    if not need_to_generate:
        current_basic_constraints_value: Optional[BasicConstraints] = None
        current_basic_constraints_critical: Optional[bool] = None
        try:
            current_basic_constraints: Extension[BasicConstraints] = (
                _x590_certificate.extensions.get_extension_for_class(BasicConstraints)
            )
            current_basic_constraints_value = current_basic_constraints.value
            current_basic_constraints_critical = current_basic_constraints.critical
        except ExtensionNotFound:
            pass
        except Exception as e:
            raise VaultOpsRetryError("Something went wrong") from e

        if expected_basic_constraints_value != current_basic_constraints_value:
            need_to_generate = True
            need_to_generate_reason = (
                f"Existing certificate's Basic Constraints does not match."
                f"Current: {current_basic_constraints_value} Expected: {expected_basic_constraints_value}"
            )

        if not need_to_generate and expected_basic_constraints_critical != current_basic_constraints_critical:
            need_to_generate = True
            need_to_generate_reason = (
                f"Existing certificate's Basic Constraints Critical does not match."
                f"Current: {current_basic_constraints_critical} Expected: {expected_basic_constraints_critical}"
            )

    # Subject Alternative Name
    if not need_to_generate:
        current_subject_alternative_name_value: Optional[SubjectAlternativeName] = None
        current_subject_alternative_name_critical: Optional[bool] = None
        try:
            current_subject_alternative_name: Extension[SubjectAlternativeName] = (
                _x590_certificate.extensions.get_extension_for_class(SubjectAlternativeName)
            )
            current_subject_alternative_name_value = current_subject_alternative_name.value
            current_subject_alternative_name_critical = current_subject_alternative_name.critical
        except ExtensionNotFound:
            pass
        except Exception as e:
            raise VaultOpsRetryError("Something went wrong", e) from e

        if expected_subject_alternative_name_value != current_subject_alternative_name_value:
            need_to_generate = True
            need_to_generate_reason = (
                f"Existing certificate's Subject Alternative Name does not match."
                f"Current: {current_subject_alternative_name_value} Expected: {expected_subject_alternative_name_value}"
            )

        if (
            not need_to_generate
            and expected_subject_alternative_name_critical != current_subject_alternative_name_critical
        ):
            need_to_generate = True
            need_to_generate_reason = (
                f"Existing certificate's Subject Alternative Name Critical does not match. "
                f"Current: {current_subject_alternative_name_critical}"
                f" Expected: {expected_subject_alternative_name_critical}"
            )

    # Validity
    if not need_to_generate:
        current_not_valid_before = _x590_certificate.not_valid_before
        current_not_valid_after = _x590_certificate.not_valid_after

        # Check if existing certificate is expired
        if current_not_valid_after < now:
            need_to_generate = True
            need_to_generate_reason = "Existing certificate is expired"

        # Check if existing certificate is not valid yet
        if not need_to_generate and current_not_valid_before > now:
            need_to_generate = True
            need_to_generate_reason = "Existing certificate is not valid yet"

        # Check if existing certificates validity is more than Issuer Validity
        if not need_to_generate and certificate_authority:
            certificate_authority_certificate = certificate_authority[0]
            issuer_valid_till = certificate_authority_certificate.not_valid_after
            if current_not_valid_after > issuer_valid_till:
                need_to_generate = True
                need_to_generate_reason = "Existing certificate's validity is more than Issuer Validity"

    if need_to_generate:
        _x590_certificate = builder.sign(
            certificate_authority_private_key, hashes.SHA256(), default_backend()  # type: ignore
        )

    certificate_bytes: bytes = _x590_certificate.public_bytes(
        encoding=serialization.Encoding.PEM,
    )

    certificate_content = certificate_bytes.decode("utf-8")

    certificate_full_chain: str = certificate_content

    if certificate_authority:
        certificate_authority_certificate = certificate_authority[0]
        certificate_authority_certificate_bytes: bytes = certificate_authority_certificate.public_bytes(
            encoding=serialization.Encoding.PEM,
        )
        certificate_full_chain = certificate_content + certificate_authority_certificate_bytes.decode("utf-8")

    if certificate_path:
        if os.path.exists(certificate_path):
            os.remove(certificate_path)
        with open(certificate_path, "w", encoding="utf-8") as f:
            f.write(certificate_full_chain)
        os.chmod(certificate_path, certificate_file_mode)
    generated_certificate = GeneratedCertificate(
        certificate=_x590_certificate,
        certificate_content=certificate_content,
        need_to_generate=need_to_generate,
        need_to_generate_reason=need_to_generate_reason,
        certificate_full_chain=certificate_full_chain,
    )
    return generated_certificate
