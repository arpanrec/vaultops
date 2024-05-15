from pydantic import BaseModel, Field

from .github_bot import GitHubBotDetails
from ..models.github_prod import GitHubProdDetails


class GitHubDetails(BaseModel):
    """
    Represents the GitHub details required for interacting with GitHub.
    """

    github_prod: GitHubProdDetails = Field(description="The GitHub production details.")
    github_bot: GitHubBotDetails = Field(description="The GitHub bot details.")
