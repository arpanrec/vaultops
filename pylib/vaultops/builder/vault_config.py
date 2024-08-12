import logging
import os
import time
from typing import Any, Dict, Union

import yaml

from ..models.vault_config import VaultConfig

LOGGER = logging.getLogger(__name__)


def build_vault_config(ansible_inventory: Union[str, Dict[str, Any]]) -> VaultConfig:
    """
    Build the VaultConfig object from the given configuration.
    """

    ansible_inventory_dict: Dict[str, Any] = {"run_id": time.strftime("%Y-%m-%d-%H-%M-%S")}
    if isinstance(ansible_inventory, str):
        LOGGER.info("Reading inventory file: %s", str(ansible_inventory))
        with open(str(ansible_inventory), "r", encoding="utf-8") as ansible_inventory_file:
            ansible_inventory_dict.update(yaml.safe_load(ansible_inventory_file))
    else:
        ansible_inventory_dict.update(ansible_inventory)

    # Ensure that the vaultops_tmp_dir_path exists and is an absolute path
    vaultops_tmp_dir_path = os.path.abspath(ansible_inventory_dict["vaultops_tmp_dir_path"])
    os.makedirs(vaultops_tmp_dir_path, exist_ok=True)
    ansible_inventory_dict["vaultops_tmp_dir_path"] = vaultops_tmp_dir_path

    # storage_config can be a file path or a dictionary
    storage_config_val = ansible_inventory_dict["storage_config"]
    if isinstance(storage_config_val, str):
        LOGGER.info("Reading storage config file: %s", str(storage_config_val))
        with open(str(storage_config_val), "r", encoding="utf-8") as storage_config_file:
            ansible_inventory_dict["storage_config"] = yaml.safe_load(storage_config_file)

    # vault_config can be a file path or a dictionary
    vault_config_val = ansible_inventory_dict["vault_config"]
    if isinstance(vault_config_val, str):
        LOGGER.info("Reading vault config file: %s", str(vault_config_val))
        with open(str(vault_config_val), "r", encoding="utf-8") as vault_config_file:
            ansible_inventory_dict["vault_config"] = yaml.safe_load(vault_config_file)

    vault_config = VaultConfig.model_validate(ansible_inventory_dict, strict=False)

    return vault_config
