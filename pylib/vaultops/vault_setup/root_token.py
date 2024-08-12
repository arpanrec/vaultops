#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enables the generation of a new root token in HashiCorp Vault.
"""
import base64
import logging
import time
from typing import Any, Dict, List, Optional, Union

import hvac  # type: ignore
from hvac.exceptions import InternalServerError, InvalidPath, InvalidRequest  # type: ignore
from prettytable import PrettyTable

from .. import VaultOpsRetryError
from ..models.ha_client import VaultHaClient
from ..models.root_token import VaultNewRootToken
from ..models.vault_config import VaultConfig
from ..models.vault_raft_node_hvac import VaultRaftNodeHvac

LOGGER = logging.getLogger(__name__)


def _calculate_new_root(encoded_root_token: str, otp: str) -> str:
    """
    Calculates a new root token using the specified encoded root token and OTP.

    Args:
        encoded_root_token (str): The encoded root token to use for calculating the new root token.
        otp (str): The OTP to use for calculating the new root token.

    Returns:
        str: The new root token.
    """
    root_token = base64.b64decode(bytearray(encoded_root_token, "ascii") + b"==")
    otp_bytes = bytearray(otp, "ascii")
    final_root_token_bytes = bytearray()
    for i, j in zip(root_token, otp_bytes):
        final_root_token_bytes.append(i ^ j)
    return str(final_root_token_bytes.decode(encoding="utf-8", errors="strict"))


def regenerate_root_token(  # pylint: disable=too-many-arguments, too-many-locals
    ready_node_details: VaultRaftNodeHvac,
    vault_config: VaultConfig,
    cancel_root_generation: bool = True,
    calculate_new_root: bool = True,
) -> VaultNewRootToken:
    """
    Generates the root token for Vault using the specified raft node and unseal keys.

    Args:
        ready_node_details (VaultRaftNodeHvac):
            - A dictionary containing information about the raft node to use for generating the root token.
        vault_config (VaultConfig): Vault secrets object containing unseal keys.
        cancel_root_generation (bool, optional):
            - If True, cancels the root token generation process if any is in progress. # pylint: disable=line-too-long
        calculate_new_root (bool, optional): If True, calculates a new root from the root token and OTP.

    Returns:
        VaultNewRootToken: A dictionary containing information about the generated root token.
    """

    vault_cluster_keys: Optional[Dict[str, Any]] = vault_config.unseal_keys()
    if vault_cluster_keys is None:
        raise VaultOpsRetryError("Vault cluster unseal keys not found in secrets.")
    keys_base64: List[str] = vault_cluster_keys["keys_base64"]
    unseal_keys: List[str] = [
        base64.b64decode(unseal_key, altchars=None, validate=False).hex() for unseal_key in list(keys_base64)
    ]

    vault_client: hvac.Client = ready_node_details.hvac_client
    new_root: Optional[str] = None
    try:
        read_root_generation_progress_response = vault_client.sys.read_root_generation_progress()
    except InternalServerError as e:
        if e.text is not None and "local node not active but active cluster node not found" in e.text:
            raise VaultOpsRetryError(
                "Vault cluster lost quorum recovery, You might need to check 'Vault cluster lost quorum recovery' "
                "from https://developer.hashicorp.com/vault/tutorials/raft/raft-lost-quorum"
            ) from e
        raise e
    except Exception as e:
        raise e
    required_num_of_unseal_keys = read_root_generation_progress_response["required"]
    provided_num_of_unseal_keys = len(unseal_keys)
    if provided_num_of_unseal_keys < required_num_of_unseal_keys:
        raise VaultOpsRetryError(
            f"Number of unseal keys provided ({provided_num_of_unseal_keys}) "
            f"is less than the required number of unseal keys ({required_num_of_unseal_keys})."
        )

    if read_root_generation_progress_response["started"]:
        if cancel_root_generation:
            vault_client.sys.cancel_root_generation()
        else:
            raise VaultOpsRetryError("Root token generation is already in progress.")

    start_generate_root_response = vault_client.sys.start_root_token_generation()

    otp = start_generate_root_response["otp"]
    nonce = start_generate_root_response["nonce"]
    generate_root_response: Dict[str, Any] = {}
    for unseal_key in unseal_keys:
        generate_root_response = vault_client.sys.generate_root(key=unseal_key, nonce=nonce)

        if generate_root_response["progress"] == generate_root_response["required"]:
            break

    encoded_root_token: str = generate_root_response["encoded_root_token"]

    if not encoded_root_token:
        raise VaultOpsRetryError("Root token could not be generated.")

    if calculate_new_root:
        new_root = _calculate_new_root(encoded_root_token, otp)

    return VaultNewRootToken(
        otp=otp,
        generate_root_response=generate_root_response,
        encoded_root_token=encoded_root_token,
        new_root=new_root,
    )


# pylint: disable=too-many-locals,too-many-branches,too-many-statements
def vault_token_revoke(vault_client: Union[VaultHaClient, VaultRaftNodeHvac]):
    """
    Revoke all tokens and destroy all AppRole secret ID accessors in HashiCorp Vault.
    Args:
        vault_ha_client (VaultHaClient): The details of the HashiCorp Vault Raft node.
    Returns:
        None
    """

    hvac_client: hvac.Client
    if isinstance(vault_client, VaultRaftNodeHvac):
        hvac_client = vault_client.hvac_client
    elif isinstance(vault_client, VaultHaClient):
        hvac_client = vault_client.hvac_client()
    else:
        raise ValueError(f"Unsupported vault_client type: {type(vault_client)}")

    current_accessor = hvac_client.auth.token.lookup_self().get("data").get("accessor")
    payload = hvac_client.list("auth/token/accessors")
    keys = payload["data"]["keys"]
    pretty_table_tokens = PrettyTable()
    pretty_table_tokens.field_names = [
        "Display Name",
        "Creation Time",
        "Expiration Time",
        "Policies",
        "Token Accessor",
        "Revoked",
    ]

    for key in keys:
        LOGGER.debug("Revoking token with accessor: %s", key)
        try:
            token_lookup_res = hvac_client.lookup_token(key, accessor=True)
        except (InvalidPath, InvalidRequest) as e:
            LOGGER.warning("Error looking up token with accessor %s: %s", key, e)
            pretty_table_tokens.add_row(["", "", "", "", key, f"False : {e}"])
            continue
        except Exception as e:  # pylint: disable=broad-except
            raise ValueError(f"Error looking up token with accessor {key}: {e}") from e
        display_name = token_lookup_res["data"]["display_name"]
        creation_date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(token_lookup_res["data"]["creation_time"]))
        expire_time = token_lookup_res["data"]["expire_time"]
        policies = token_lookup_res["data"]["policies"]
        accessor = key
        if accessor != current_accessor:
            try:
                hvac_client.revoke_token(accessor, accessor=True)
                pretty_table_tokens.add_row([display_name, creation_date, expire_time, policies, accessor, True])
            except InvalidRequest as e:
                LOGGER.info("Error revoking token with accessor %s: %s", key, e)
                pretty_table_tokens.add_row(
                    [display_name, creation_date, expire_time, policies, accessor, f"False : {e}"]
                )
            except Exception as e:  # pylint: disable=broad-except
                raise ValueError(f"Error revoking token with accessor {key}: {e}") from e

        else:
            pretty_table_tokens.add_row(
                [display_name, creation_date, expire_time, policies, accessor, "False : current_accessor"]
            )
    LOGGER.info("Revoked all tokens \n%s", pretty_table_tokens)

    pretty_table_approle = PrettyTable()
    pretty_table_approle.field_names = [
        "Auth Mount",
        "RoleName",
        "Secret ID Accessor",
        "Revoked",
    ]

    auth_methods = hvac_client.sys.list_auth_methods()
    for auth_method in auth_methods["data"]:
        auth_method_dict = auth_methods["data"][auth_method]
        if auth_method_dict["type"] == "approle":
            list_of_approles = hvac_client.auth.approle.list_roles(mount_point=auth_method)
            for role_name in list_of_approles["data"]["keys"]:
                try:
                    list_secret_id_accessors = hvac_client.auth.approle.list_secret_id_accessors(
                        role_name, mount_point=auth_method
                    )
                except InvalidPath as e:
                    LOGGER.info("Error listing secret id accessors for role %s: %s", role_name, e)
                    list_secret_id_accessors = {"data": {"keys": []}}
                except Exception as e:  # pylint: disable=broad-except
                    raise ValueError(f"Error listing secret id accessors for role {role_name}: {e}") from e
                for secret_id_accessor in list_secret_id_accessors["data"]["keys"]:
                    hvac_client.auth.approle.destroy_secret_id_accessor(
                        role_name, secret_id_accessor, mount_point="approle"
                    )
                    pretty_table_approle.add_row([auth_method, role_name, secret_id_accessor, True])
    LOGGER.info("Revoked all approle secret id accessors \n%s", pretty_table_approle)
    LOGGER.info("Revoking Vault token and logging out")
    hvac_client.logout(revoke_token=True)
    LOGGER.info("Current authentication status: %s", hvac_client.is_authenticated())
