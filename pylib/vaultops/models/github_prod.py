from pydantic import BaseModel, Field


class GitHubProdDetails(BaseModel):
    """
    Represents the GitHub details required for interacting with GitHub.
    """

    GH_PROD_API_TOKEN: str = Field(description="The GitHub production API token.")
