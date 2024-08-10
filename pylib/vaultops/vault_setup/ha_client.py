#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module for interacting with HashiCorp Vault in a high-availability (HA) setup.
"""
import base64
import logging
from typing import Dict, Optional, Set

import yaml
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes
from cryptography.hazmat.primitives.serialization import BestAvailableEncryption, pkcs12
from cryptography.x509 import Certificate, load_pem_x509_certificate

from ..builder.vault_raft_node import build_raft_server_nodes_map
from ..models.certificate import (
    CertificateDetails,
    CertificateDetailsBasicConstraints,
    CertificateDetailsKeyUsage,
    CertificateProperties,
    GeneratedCertificate,
)
from ..models.ha_client import VaultHaClient
from ..models.pki_private_key import GeneratedPrivateKey, PrivateKeyProperties
from ..models.vault_config import VaultConfig
from ..models.vault_raft_node import VaultRaftNode
from ..models.vault_secrets import VaultSecrets
from .certificate import generate_x590_certificate
from .private_key import generate_private_key

LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-locals
def create_ha_client(
    vault_config: VaultConfig,
    rsa_root_ca_key: PrivateKeyTypes,
    rsa_root_ca_cert: Optional[Certificate],
) -> VaultHaClient:
    """
    Rotate the access configuration for the Vault HA (High Availability) setup.
    Args:
        vault_config (VaultConfig): An instance of the VaultConfig class used to create/update secrets in Vault.
        rsa_root_ca_key (PrivateKeyTypes): The RSA root CA key.
        rsa_root_ca_cert (Certificate): The RSA root CA certificate.
    Returns:
        VaultHaClient: An instance of the VaultHaClient class.
    """

    vault_secrets: VaultSecrets = vault_config.vault_secrets

    if not rsa_root_ca_cert:
        rsa_root_ca_cert = load_pem_x509_certificate(
            vault_secrets.root_pki_details.root_ca_cert_pem.encode("utf-8"), default_backend()
        )

    all_san: Set[str] = {vault_config.vault_ha_hostname_san_entry}
    server_raft_nodes: Dict[str, Dict[str, VaultRaftNode]] = build_raft_server_nodes_map(vault_config)
    for _, servers in server_raft_nodes.items():
        for _, raft_node in servers.items():
            all_san.update(list(raft_node.subject_alt_name))

    _vault_ha_rsa_client_private_key: GeneratedPrivateKey = generate_private_key(PrivateKeyProperties())

    _vault_ha_rsa_client_certificate: GeneratedCertificate = generate_x590_certificate(
        rsa_private_key=_vault_ha_rsa_client_private_key.private_key,
        certificate_authority=(rsa_root_ca_cert, rsa_root_ca_key),
        certificate_properties=CertificateProperties(
            certificate_details=CertificateDetails(
                name={"COMMON_NAME": "vault_ha_client_cert"},
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
                subject_alternative_name=list(all_san),
                not_valid_after=90,
                extended_key_usage=["CLIENT_AUTH"],
                extended_key_usage_critical=True,
            )
        ),
    )
    _vault_ha_rsa_client_p12_certificate = pkcs12.serialize_key_and_certificates(
        name=b"vault_master_client_certificate",
        key=_vault_ha_rsa_client_private_key.private_key,
        cert=_vault_ha_rsa_client_certificate.certificate,
        cas=[rsa_root_ca_cert],
        encryption_algorithm=BestAvailableEncryption(
            vault_secrets.vault_admin_userpass_details.vault_admin_client_cert_p12_passphrase.encode("utf-8")
        ),
    )

    admin_user: str = vault_secrets.vault_admin_userpass_details.vault_admin_user
    admin_password: str = vault_secrets.vault_admin_userpass_details.vault_admin_password
    userpass_mount: str = vault_secrets.vault_admin_userpass_details.vault_admin_userpass_mount_path
    policy_name: str = vault_secrets.vault_admin_userpass_details.vault_admin_policy_name
    client_cert_pem: str = str(_vault_ha_rsa_client_certificate.certificate_full_chain)
    client_key_pem: str = str(_vault_ha_rsa_client_private_key.private_key_content)
    vault_ha_hostname: str = vault_secrets.vault_ha_hostname
    vault_ha_port: int = vault_secrets.vault_ha_port
    client_cert_p12_base64: str = base64.b64encode(_vault_ha_rsa_client_p12_certificate).decode("utf-8")
    root_ca_cert_pem: str = vault_secrets.root_pki_details.root_ca_cert_pem

    ha_client: VaultHaClient = VaultHaClient(
        admin_user=admin_user,
        admin_password=admin_password,
        userpass_mount=userpass_mount,
        policy_name=policy_name,
        client_cert_pem=client_cert_pem,
        client_key_pem=client_key_pem,
        vault_ha_hostname=vault_ha_hostname,
        vault_ha_port=vault_ha_port,
        client_cert_p12_base64=client_cert_p12_base64,
        client_cert_p12_passphrase=vault_secrets.vault_admin_userpass_details.vault_admin_client_cert_p12_passphrase,
        root_ca_cert_pem=root_ca_cert_pem,
    )

    LOGGER.info("Writing data to %s", f"{vault_config.vaultops_tmp_dir_path}/vault-ha-client.yml")
    with open(f"{vault_config.vaultops_tmp_dir_path}/vault-ha-client.yml", "w", encoding="utf-8") as f:
        yaml.dump(ha_client.model_dump(), f, default_flow_style=False, default_style="|")

    return VaultHaClient(**ha_client.model_dump(), vault_config=vault_config)
