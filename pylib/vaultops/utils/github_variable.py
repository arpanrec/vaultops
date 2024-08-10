import base64
from typing import Optional

from github import Auth, Github


# pylint: disable=too-many-arguments,too-many-locals,too-many-return-statements,too-many-branches,too-many-statements
def github_variable(
    pat: str,
    name: str,
    unencrypted_value: str,
    environment: Optional[str] = None,
    repository: Optional[str] = None,
    organization: Optional[str] = None,
    is_base64_encoded: bool = False,
    visibility: Optional[str] = None,
    is_secret: bool = True,
    state: str = "present",
    api_ep: str = "https://api.github.com",
) -> None:
    """
    Performs Create, Read, Update, and Delete (CRUD) operations.

    This function is responsible for performing CRUD operations
    on GitHub Action Secrets based on the provided parameters.

    Parameters:
        api_ep: (str): The GitHub API endpoint. Optional.
        pat: (str): The personal access token (PAT) to authenticate with GitHub. Required.
        is_secret: (bool): Whether the value is a secret. Optional.
        environment: (str): The environment to which the secret belongs. Optional.
        unencrypted_value: (str): The unencrypted value of the secret. Required.
        is_base64_encoded: (bool): Whether to base64 encode the secret. Optional.
        visibility (str): The visibility of the secret. Optional.
        state (str): The state of the secret. Optional.
        repository (str): The name of the repository. Optional.
        organization (str): The organization of the repository. Optional.
        name (str): The name of the secret. Required.

    Returns:
        dict: A dictionary containing the results of the CRUD operation.
    """

    if repository and organization:
        raise ValueError("repository and organization are mutually exclusive")

    if repository and visibility:
        raise ValueError("repository and visibility are mutually exclusive")

    if not repository and not organization:
        raise ValueError("repository or organization is mandatory")

    if organization and environment:
        raise ValueError("organization and environment are mutually exclusive")

    if state not in ("present", "absent"):
        raise ValueError(f"state should be either present or absent, {state}")

    if visibility and visibility not in ["private", "all", "selected"]:
        raise ValueError("visibility should in 'private', 'all', 'selected'")

    if state == "absent" and unencrypted_value:
        raise ValueError("unencrypted_value is not required for state absent")

    if state == "absent" and is_base64_encoded:
        raise ValueError("is_base64_encoded is not required for state absent")

    if state == "absent" and visibility:
        raise ValueError("visibility is not required for state absent")

    if state == "present" and not unencrypted_value:
        raise ValueError("unencrypted_value is required for state present")

    if is_base64_encoded:
        unencrypted_value = base64.b64encode(unencrypted_value.encode()).decode()

    if not visibility:
        visibility = "all"

    auth = Auth.Token(pat)
    github = Github(base_url=api_ep, auth=auth)
    if state == "present":
        if repository:
            repo = github.get_repo(repository)
            if environment:
                env = repo.get_environment(environment)
                if is_secret:
                    env.create_secret(name, unencrypted_value)
                else:
                    env.create_variable(name, unencrypted_value)
            else:
                if is_secret:
                    repo.create_secret(name, unencrypted_value)
                else:
                    repo.create_variable(name, unencrypted_value)
        else:
            org = github.get_organization(str(organization))
            if is_secret:
                org.create_secret(name, unencrypted_value, visibility)
            else:
                org.create_variable(name, unencrypted_value, visibility)
    else:
        if repository:
            repo = github.get_repo(repository)
            if environment:
                env = repo.get_environment(environment)
                if is_secret:
                    env.delete_secret(name)
                else:
                    env.delete_variable(name)
            else:
                if is_secret:
                    repo.delete_secret(name)
                else:
                    repo.delete_variable(name)
        else:
            raise ValueError("organization delete not supported")
