#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module provides functions to create terraform vars file for codifiedvault.

The functions in this module are used to generate terraform vars file and backend vars file
for codifiedvault, which is a tool for managing HashiCorp Vault infrastructure as code.

Functions:
- create_terraform_tf_vars: Create terraform vars file for codifiedvault.

"""

import json
import logging
import os
import shutil
import time
from typing import Any, Dict

from python_terraform import Terraform  # type: ignore

from ..models.ha_client import VaultHaClient
from ..models.vault_config import VaultConfig

LOGGER = logging.getLogger(__name__)


def terraform_apply(  # pylint: disable=too-many-locals
    vault_config: VaultConfig,
    vault_ha_client: VaultHaClient,
):
    """
    Create terraform vars file for codifiedvault
    """

    LOGGER.info("Removing old codifiedvault/.terraform directory if exists")
    if os.path.exists("codifiedvault/.terraform"):
        shutil.rmtree("codifiedvault/.terraform", ignore_errors=False)

    epoch_time = str(int(time.time()))

    tf_state_file = os.path.join(vault_config.vaultops_tmp_dir_path, "terraform.tfstate")
    tf_state_file_bak = f"{tf_state_file}_bak_{epoch_time}"
    backend_tf_vars: Dict[str, Any] = {"path": tf_state_file}
    current_tf_state = vault_config.tf_state()
    if current_tf_state is not None:
        with open(tf_state_file, "w", encoding="utf-8") as f:
            f.write(str(current_tf_state))
    else:
        if os.path.exists(tf_state_file):
            os.remove(tf_state_file)

    tf = Terraform(working_dir="codifiedvault", is_env_vars_included=True)
    LOGGER.info("Writing backend vars in %s/backend.auto.tfvars.json", vault_config.vaultops_tmp_dir_path)
    with open(f"{vault_config.vaultops_tmp_dir_path}/backend.auto.tfvars.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(backend_tf_vars, indent=4))
    LOGGER.info("Run terraform init in codifiedvault directory")
    LOGGER.info(
        "terraform -chdir=codifiedvault init -backend-config=%s/backend.auto.tfvars.json",
        vault_config.vaultops_tmp_dir_path,
    )

    # return_code, stdout, stderr = tf.init(backend_config=backend_tf_vars, reconfigure=False)

    return_code, stdout, stderr = tf.init(
        reconfigure=False, backend_config=f"{vault_config.vaultops_tmp_dir_path}/backend.auto.tfvars.json"
    )

    LOGGER.info("Return code: %s, stdout: %s, stderr: %s", return_code, stdout, stderr)

    if return_code != 0:
        raise ValueError("Failed to run terraform init")

    tf_vars: Dict[str, Any] = {
        "codifiedvault_vault_fqdn": vault_ha_client.vault_ha_hostname,
        "codifiedvault_vault_port": vault_ha_client.vault_ha_port,
        "codifiedvault_login_username": vault_ha_client.admin_user,
        "codifiedvault_login_userpass_mount_path": vault_ha_client.userpass_mount,
        "codifiedvault_login_password": vault_ha_client.admin_password,
        "codifiedvault_vault_client_key_file": vault_ha_client.vault_client_key_file,
        "codifiedvault_vault_client_cert_file": vault_ha_client.vault_client_cert_file,
        "codifiedvault_vault_ca_file": vault_ha_client.vault_root_ca_cert_file,
    }

    LOGGER.info("Writing terraform vars in %s/secrets.auto.tfvars.json", vault_config.vaultops_tmp_dir_path)
    with open(f"{vault_config.vaultops_tmp_dir_path}/secrets.auto.tfvars.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(tf_vars, indent=4))

    apply_ret_code, apply_stdout, apply_stderr = tf.apply(
        skip_plan=True, auto_approve=True, var_file=f"{vault_config.vaultops_tmp_dir_path}/secrets.auto.tfvars.json"
    )

    LOGGER.info("Return code: %s, stdout: %s, stderr: %s", apply_ret_code, apply_stdout, apply_stderr)

    LOGGER.info("Removing old codifiedvault/.terraform directory if exists")
    if os.path.exists("codifiedvault/.terraform"):
        shutil.rmtree("codifiedvault/.terraform", ignore_errors=False)

    if apply_ret_code != 0:
        raise ValueError(f"Failed to run terraform apply. error: {apply_stderr}")

    with open(tf_state_file, "r", encoding="utf-8") as f:
        LOGGER.debug("Saving codifiedvault_tf_state")
        vault_config.tf_state(f.read())

    LOGGER.debug("Moving %s to %s", tf_state_file, tf_state_file_bak)
    shutil.move(tf_state_file, tf_state_file_bak)
