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
    ansible_inventory_dict["vaultops_tmp_dir_path"] = vaultops_tmp_dir_path

    vault_config = VaultConfig.model_validate(ansible_inventory_dict, strict=False)

    return vault_config
