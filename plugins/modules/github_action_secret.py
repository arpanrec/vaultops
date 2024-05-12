"""
Ansible Module for adding GitHub action secret.
"""

# Copyright: (c) 2022, Arpan Mandal <arpan.rec@gmail.com>
# MIT (see LICENSE or https://en.wikipedia.org/wiki/MIT_License)
from __future__ import absolute_import, division, print_function

from ansible.module_utils.basic import AnsibleModule  # type: ignore

# pylint: disable=C0103
__metaclass__ = type

from vaultops.utils.github_variable import github_variable

DOCUMENTATION = r"""
---
module: github_action_secret

short_description: Create Update Delete Github Action Secret

version_added: "1.0.0"

description: Create Update Delete Github Action Secret.

options:
    api_ep:
        description: Rest Api endpoint
        required: false
        type: str
        default: "https://api.github.com"
    pat:
        description: Github PAT.
        required: true
        type: str
    organization:
        description:
            - organization of the repository
            - If repository is missing then the secret wil be added to organization secret
        required: false
        type: str
    unencrypted_value:
        description: Plain text action secret
        required: false
        type: str
    name:
        description: Name of the secret
        required: true
        type: str
    repository:
        description: Name of the github repository.
        required: false
        type: str
    state:
        description: State of the secret.
        required: false
        type: str
        choices: ["present", "absent"]
        default: present
    visibility:
        description: Mandatory for organization secrets
        choices: ["private", "all", "selected"]
        type: str
        required: false
    is_base64_encoded:
        description: Base64 encoded secret
        type: str
        required: false
        default: false
    is_secret:
        description: Whether the value is a secret
        type: bool
        required: false
        default: true
    environment:
        description: The environment to which the secret belongs
        type: str
        required: false
author:
    - Arpan Mandal (mailto:arpan.rec@gmail.com)
"""

EXAMPLES = r"""
- name: Create or Update a repository secret
  github_action_secret:
      api_ep: "https://api.github.com"
      pat: "{{ lookup('ansible.builtin.env', 'GH_PROD_API_TOKEN') }}"
      unencrypted_value: "supersecret"
      repository: "arpanrec/github-master-controller"
      name: "ENV_SECRET1"

- name: Create or Update a organization secret
  github_action_secret:
      api_ep: "https://api.github.com"
      pat: "{{ lookup('ansible.builtin.env', 'GH_PROD_API_TOKEN') }}"
      unencrypted_value: "supersecret"
      name: "ENV_SECRET"
      organization: arpanrec
      state: present
      visibility: all

- name: Delete a repository secret
  github_action_secret:
      api_ep: "https://api.github.com"
      pat: "{{ lookup('ansible.builtin.env', 'GH_PROD_API_TOKEN') }}"
      repository: "arpanrec/github-master-controller"
      name: "ENV_SECRET"
      state: absent
"""

RETURN = r"""
public_key:
    description: Public Key of the repository
    type: str
    returned: if state == present
public_key_id:
    description: Public Key id of the repository
    type: str
    returned: if state == present
secret:
    description: Encrypted secret
    type: str
    returned: if state == present
"""


# pylint: disable=inconsistent-return-statements
def run_module():
    """
    Ansible main module
    """
    # define available arguments/parameters a user can pass to the module
    module_args = {
        "api_ep": {
            "type": "str",
            "required": False,
            "default": "https://api.github.com",
        },
        "pat": {"type": "str", "required": True, "no_log": True},
        "organization": {"type": "str", "required": False},
        "unencrypted_value": {"type": "str", "required": False, "no_log": True},
        "name": {"type": "str", "required": True},
        "repository": {"type": "str", "required": False},
        "state": {
            "type": "str",
            "required": False,
            "default": "present",
            "choices": ["present", "absent"],
        },
        "visibility": {
            "type": "str",
            "required": False,
            "choices": ["private", "all", "selected"],
        },
        "environment": {"type": "str", "required": False},
        "is_secret": {"type": "bool", "required": False, "default": "true"},
        "is_base64_encoded": {"type": "bool", "required": False, "default": "false"},
    }

    module = AnsibleModule(
        argument_spec=module_args,
    )

    try:
        github_variable(
            api_ep=module.params["api_ep"],
            pat=module.params["pat"],
            unencrypted_value=module.params["unencrypted_value"],
            name=module.params["name"],
            repository=module.params["repository"],
            organization=module.params["organization"],
            state=module.params["state"],
            environment=module.params["environment"],
            is_secret=bool(module.params["is_secret"]),
            visibility=module.params["visibility"],
            is_base64_encoded=bool(module.params["is_base64_encoded"]),
        )
        module.exit_json(changed=True)
    except Exception as error:  # pylint: disable=broad-except
        module.fail_json(msg=str(error))


def main():
    """
    Python Main Module
    """
    run_module()


if __name__ == "__main__":
    main()
