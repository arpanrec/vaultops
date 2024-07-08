import logging
import os
from typing import Any, Dict, Union

import yaml

from ..models.vault_config import VaultConfig

LOGGER = logging.getLogger(__name__)


def build_vault_config(ansible_inventory: Union[str, Dict[str, Any]]) -> VaultConfig:
    """
    Build the VaultConfig object from the given configuration.
    """

    ansible_inventory_dict: Dict[str, Any]

    if isinstance(ansible_inventory, str):
        LOGGER.info("Reading inventory file: %s", str(ansible_inventory))
        with open(str(ansible_inventory), "r", encoding="utf-8") as ansible_inventory_file:
            ansible_inventory_dict = yaml.safe_load(ansible_inventory_file)
    else:
        ansible_inventory_dict = ansible_inventory

    vaultops_tmp_dir_path = os.path.abspath(ansible_inventory_dict["vaultops_tmp_dir_path"])
    os.makedirs(vaultops_tmp_dir_path, exist_ok=True)

    vaultops_s3_aes256_sse_customer_key_base64 = ansible_inventory_dict["vaultops_s3_aes256_sse_customer_key_base64"]
    vaultops_s3_bucket_name = ansible_inventory_dict["vaultops_s3_bucket_name"]
    vaultops_s3_endpoint_url = ansible_inventory_dict["vaultops_s3_endpoint_url"]
    vaultops_s3_access_key = ansible_inventory_dict["vaultops_s3_access_key"]
    vaultops_s3_secret_key = ansible_inventory_dict["vaultops_s3_secret_key"]
    vaultops_s3_signature_version = ansible_inventory_dict.get("vaultops_s3_signature_version", "s3v4")
    vaultops_s3_region = ansible_inventory_dict["vaultops_s3_region"]

    vault_config = VaultConfig(
        vaultops_tmp_dir_path=vaultops_tmp_dir_path,
        vaultops_s3_aes256_sse_customer_key_base64=vaultops_s3_aes256_sse_customer_key_base64,
        vaultops_s3_endpoint_url=vaultops_s3_endpoint_url,
        vaultops_s3_bucket_name=vaultops_s3_bucket_name,
        vaultops_s3_access_key=vaultops_s3_access_key,
        vaultops_s3_secret_key=vaultops_s3_secret_key,
        vaultops_s3_signature_version=vaultops_s3_signature_version,
        vaultops_s3_region=vaultops_s3_region,
    )

    return vault_config
