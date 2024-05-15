from pydantic import BaseModel, Field


class GitHubBotDetails(BaseModel):
    """
    Represents the GitHub bot details required for interacting with GitHub.
    """

    GH_BOT_API_TOKEN: str = Field(description="The GitHub bot API token.")
    GH_BOT_GPG_PRIVATE_KEY: str = Field(description="The GitHub Actions GPG private key.")
    GH_BOT_GPG_PASSPHRASE: str = Field(description="The GitHub Actions GPG passphrase.")
