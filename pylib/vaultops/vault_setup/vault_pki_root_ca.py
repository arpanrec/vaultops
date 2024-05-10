#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains the functions to set up the root pki in Vault
"""
import json
import logging
from typing import Optional, Tuple

import hvac  # type: ignore
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes
from cryptography.x509 import Certificate

from ..models.ha_client import VaultHaClient

LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-locals
def setup_root_pki(vault_ha_client: VaultHaClient, root_ca_rsa: Tuple[Certificate, PrivateKeyTypes]) -> None:
    """
    This function sets up the root pki in Vault

    :param vault_ha_client: VaultHaClient object
    :param root_ca_rsa: Tuple of Certificate and PrivateKeyTypes
    """

    hvac_client: hvac.Client = vault_ha_client.hvac_client()

    mount_point = "root-ca"
    def_issuer_ref: Optional[str] = None

    enabled_secret_engines = hvac_client.sys.list_mounted_secrets_engines()["data"]

    if f"{mount_point}/" not in enabled_secret_engines:
        enable_secrets_engine_res = hvac_client.sys.enable_secrets_engine(
            backend_type="pki", path=mount_point, options={"max_lease_ttl": "350400h", "default_lease_ttl": "350400h"}
        )
        LOGGER.debug("Enable Secrets Engine: %s", enable_secrets_engine_res)

    hvac_client.sys.tune_mount_configuration(path=mount_point, default_lease_ttl="350400h", max_lease_ttl="350400h")

    current_ca_certificate: str = hvac_client.secrets.pki.read_ca_certificate(mount_point=mount_point)
    LOGGER.debug("Current CA Certificate: %s", current_ca_certificate)

    rsa_cert, rsa_key = root_ca_rsa

    root_ca_cert_pem = rsa_cert.public_bytes(encoding=serialization.Encoding.PEM).decode("utf-8")
    root_ca_serial_number = f"{rsa_cert.serial_number:x}".upper()
    LOGGER.info("Root CA Serial Number: %s", root_ca_serial_number)

    root_key_pem = rsa_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    submit_ca_information = hvac_client.secrets.pki.submit_ca_information(
        mount_point=mount_point, pem_bundle=f"{root_key_pem}{root_ca_cert_pem}"
    )
    LOGGER.debug("Submit CA Information: %s", json.dumps(submit_ca_information, indent=4))

    LOGGER.info("Updating the default issuer to root-ca-issuer")
    list_issuers = hvac_client.secrets.pki.list_issuers(mount_point=mount_point)["data"]["key_info"]
    for issuer_ref, issuer_info in list_issuers.items():
        if issuer_info["serial_number"].replace(":", "").upper() == root_ca_serial_number.upper():
            set_default_issuer = hvac_client.write_data(
                path=f"{mount_point}/config/issuers",
                data={
                    "default": issuer_ref,
                    "default_follows_latest_issuer": True,
                },
            )
            LOGGER.debug("Set Default Issuer: %s", json.dumps(set_default_issuer, indent=4))
            LOGGER.info("Default Issuer Reference: %s", issuer_ref)
            def_issuer_ref = issuer_ref

    list_issuers_post_set_default = hvac_client.secrets.pki.list_issuers(mount_point=mount_point)["data"]["key_info"]

    for issuer_ref, issuer_info in list_issuers_post_set_default.items():
        LOGGER.info("Issuer reference: %s", issuer_ref)
        LOGGER.debug("Issuer info: %s", json.dumps(issuer_info, indent=4))
        if issuer_info["serial_number"].replace(":", "").upper() != root_ca_serial_number.upper():
            LOGGER.info("Deleting issuer: %s", issuer_ref)
            delete_issuer = hvac_client.secrets.pki.delete_issuer(mount_point=mount_point, issuer_ref=issuer_ref)
            LOGGER.debug("Delete Issuer: %s", json.dumps(delete_issuer, indent=4))

    update_root_ca_issuer = hvac_client.write_data(
        path=f"{mount_point}/issuer/{def_issuer_ref}",
        data={"issuer_name": "root-ca-issuer"},
    )
    LOGGER.info("Root CA Issuer Reference: %s", def_issuer_ref)
    LOGGER.debug("Update Root CA Issuer: %s", json.dumps(update_root_ca_issuer, indent=4))
