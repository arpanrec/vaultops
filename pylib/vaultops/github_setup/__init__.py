import logging

from .github import add_vault_access_to_github
from .github_bot import add_gpg_to_bot_github
from ..models.ha_client import VaultHaClient

LOGGER = logging.getLogger(__name__)


def setup_github(vault_ha_client: VaultHaClient):
    """
    Setup GitHub access for the bot and users.
    """

    LOGGER.info("Adding vault access to GitHub user repositories")
    add_vault_access_to_github(vault_ha_client=vault_ha_client)

    LOGGER.info("Add gpg key to bot GitHub account")
    add_gpg_to_bot_github(vault_ha_client=vault_ha_client)
