#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module is responsible for initializing and unsealing a HashiCorp Vault cluster.
It performs the following tasks:
- Reads the inventory YAML file to get the Vault secrets and server configurations.
- Builds the map of Raft server nodes.
- Creates a hvac client for each Raft node and establishes a session.
- Generates client certificates for each Raft node using a root CA certificate.
- Unseals the Vault using the provided unseal keys.
- Finds a ready Vault node.
- Generates a new root token for the Vault cluster.
- Updates all the clients with the new root token.
- Removes unmatched nodes from the cluster.
- Adds new nodes to the cluster.
- Validates the Raft nodes in the cluster.
- Sets up service admin access.

This module is intended to be executed as the main entry point of the installation process.
"""

import argparse
import logging
import os
import sys
import time

from . import VaultOpsRetryError, VaultOpsSafeExit, vault_setup
from .github_setup import setup_github
from .models.ha_client import VaultHaClient

IS_DEBUG: bool = False
LOGGING_LEVEL: int = logging.INFO
if str(os.environ.get("DEBUG", "False")).lower() == "true":
    IS_DEBUG = True
    LOGGING_LEVEL = logging.DEBUG

print("Remove existing log handlers")
root = logging.getLogger()
if root.handlers:
    for handler in root.handlers:
        root.removeHandler(handler)

logging.basicConfig(
    level=LOGGING_LEVEL,
    format="%(asctime)s - %(levelname)s - %(name)s.%(funcName)s():%(lineno)d:- %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

LOGGER = logging.getLogger(__name__)


def main() -> None:
    """
    Main function for initializing and unsealing the vault.

    This function attempts to initialize and unseal the vault using the provided inventory.
    It retries the operation a maximum of `max_vaultops_retries` times
    with a wait time of `max_vaultops_retry_wait`  seconds between retries.
    If the operation fails after all retries, it raises a `VaultOpsRetryError`.

    Raises:
        VaultOpsRetryError: If the operation fails after all retries.

    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", default="inventory.yml")
    parser.add_argument("--github", action=argparse.BooleanOptionalAction, default=False)
    args = parser.parse_args()
    max_vaultops_retries: int = 5
    max_vaultops_retry_wait: int = 10
    while max_vaultops_retries > 0:
        max_vaultops_retries -= 1
        try:
            LOGGER.info("Initializing and unsealing vault")
            vault_ha_client: VaultHaClient = vault_setup.vault_setup(args.inventory)
            LOGGER.info("Vault setup completed successfully")

            if args.github:
                # Add vault access to GitHub user repositories
                LOGGER.info("Adding vault access to GitHub user repositories")
                setup_github(vault_ha_client=vault_ha_client)

            break

        except VaultOpsRetryError as e:  # pylint: disable=broad-except
            if max_vaultops_retries > 0:
                LOGGER.exception("%s: Error occurred while setting vault, retrying, %s", type(e), e, exc_info=True)
                LOGGER.info("Retrying in %s seconds, retries left: %s", max_vaultops_retry_wait, max_vaultops_retries)
                time.sleep(max_vaultops_retry_wait)
            else:
                raise VaultOpsRetryError("Error occurred while setting vault, retries exhausted") from e

        except VaultOpsSafeExit as e:  # pylint: disable=broad-except
            LOGGER.info("Operation completed successfully, %s", str(e))
            sys.exit(0)

        except KeyboardInterrupt as e:  # pylint: disable=broad-except
            LOGGER.info("Operation interrupted by user, %s", str(e))
            sys.exit(1)

        except Exception as e:  # pylint: disable=broad-except
            raise VaultOpsRetryError("Error occurred while setting vault, retries exhausted") from e


if __name__ == "__main__":
    main()
