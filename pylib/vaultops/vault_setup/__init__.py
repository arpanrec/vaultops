import logging
import os
from typing import Dict

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes
from cryptography.x509 import Certificate, load_pem_x509_certificate

from ..builder.vault_config import build_vault_config
from ..builder.vault_raft_node_hvac import create_raft_node_hvac
from ..models.ha_client import VaultHaClient
from ..models.vault_config import VaultConfig
from .admin_user import add_admin_user_policy
from .codifiedvault import terraform_apply
from .find_ready import find_ready
from .ha_client import create_ha_client
from .initialize import initialize_vault
from .raft_node_hvac import VaultRaftNodeHvac, update_client_with_root_token
from .raft_nodes_join import raft_ops
from .raft_snapshot import take_raft_snapshot
from .root_token import VaultNewRootToken, regenerate_root_token, vault_token_revoke
from .unseal import unseal_vault
from .vault_pki_root_ca import setup_root_pki
from .vault_secrets import update_vault_secrets

LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-statements
def vault_setup(inventory_file_name: str) -> VaultHaClient:
    """
    Setup vault
    args:
        inventory_file_name: str - inventory file name
    """

    vault_config: VaultConfig = build_vault_config(inventory_file_name)

    LOGGER.info("Loading root ca key")
    rsa_root_ca_key: PrivateKeyTypes = serialization.load_pem_private_key(
        vault_config.vault_secrets.root_pki_details.root_ca_key_pem.encode("utf-8"),
        password=vault_config.vault_secrets.root_pki_details.root_ca_key_password.encode("utf-8"),
        backend=default_backend(),
    )

    LOGGER.info("Loading root ca certificate")
    rsa_root_ca_cert: Certificate = load_pem_x509_certificate(
        vault_config.vault_secrets.root_pki_details.root_ca_cert_pem.encode("utf-8"), default_backend()
    )

    vault_root_ca_cert_file: str = os.path.join(vault_config.vaultops_tmp_dir_path, "vault_root_ca_cert.pem")
    LOGGER.info("Writing root ca certificate to %s", vault_root_ca_cert_file)
    with open(vault_root_ca_cert_file, "w", encoding="utf-8") as f:
        f.write(vault_config.vault_secrets.root_pki_details.root_ca_cert_pem)

    all_raft_nodes: Dict[str, VaultRaftNodeHvac] = create_raft_node_hvac(
        vault_config=vault_config,
        rsa_root_ca_cert=rsa_root_ca_cert,
        rsa_root_ca_key=rsa_root_ca_key,
        vault_root_ca_cert_file=vault_root_ca_cert_file,
    )

    vault_ha_client: VaultHaClient = create_ha_client(
        vault_config=vault_config,
        rsa_root_ca_key=rsa_root_ca_key,
        rsa_root_ca_cert=rsa_root_ca_cert,
    )
    LOGGER.info("Initializing vault")
    initialize_vault(all_raft_nodes=all_raft_nodes, vault_config=vault_config)

    LOGGER.info("Unsealing vault")
    unseal_vault(all_raft_nodes=all_raft_nodes, vault_config=vault_config)

    LOGGER.info("Find a ready vault node")
    ready_node_id, ready_node_details = find_ready(all_raft_nodes=all_raft_nodes)
    LOGGER.info("Ready node found: %s", ready_node_id)

    vault_sudo_token: str

    if vault_config.unseal_keys():
        LOGGER.info("Creating new root token")
        new_root_token: VaultNewRootToken = regenerate_root_token(
            ready_node_details=ready_node_details,
            vault_config=vault_config,
            calculate_new_root=True,
            cancel_root_generation=True,
        )
        LOGGER.info("New root token created")
        LOGGER.debug("New root token: %s", new_root_token.new_root)
        vault_sudo_token = str(new_root_token.new_root)
    else:
        LOGGER.info("No unseal keys found, skipping root token generation")
        vault_sudo_token = vault_ha_client.hvac_client().token

    LOGGER.info("Updating all the clients with new root token")
    update_client_with_root_token(all_raft_nodes=all_raft_nodes, new_root_token=vault_sudo_token)

    LOGGER.info("Remove, Add and Validate raft nodes")
    raft_ops(all_raft_nodes=all_raft_nodes, ready_node_details=ready_node_details)

    if vault_config.unseal_keys():
        LOGGER.info("Setting up service admin access")
        add_admin_user_policy(ready_node_details=ready_node_details, vault_ha_client=vault_ha_client)
    else:
        LOGGER.info("No unseal keys found, skipping service admin access, assuming it is already set up")

    LOGGER.info("Creating root pki")
    setup_root_pki(vault_ha_client=vault_ha_client, root_ca_rsa=(rsa_root_ca_cert, rsa_root_ca_key))

    LOGGER.info("Codifying vault")
    terraform_apply(vault_config=vault_config, vault_ha_client=vault_ha_client)

    LOGGER.info("Revoking all tokens and secret ID accessors")
    if vault_config.unseal_keys():
        vault_token_revoke(vault_client=ready_node_details)
    else:
        vault_token_revoke(vault_client=vault_ha_client)

    LOGGER.info("Updating external service secrets")
    update_vault_secrets(vault_ha_client=vault_ha_client, vault_config=vault_config)

    LOGGER.info("Taking a raft snapshot")
    take_raft_snapshot(vault_ha_client=vault_ha_client, vault_config=vault_config)

    return vault_ha_client
