# Deployment

* Make sure the [Prerequisites](PREREQUISITES.md) are met.

## Patch the systems

Update the servers. This is not needed if the servers are already updated.

```bash
ansible-playbook playbook.yml --tags patch
```

* If a server is added newly to the inventory then set access from local machine to the server,
and set `root_ca_key_pem_as_ansible_priv_ssh_key` to False in [inventory.yml](./inventory.yml) file for the first run.

## Install Vault on the Vault server

Install vault on the vault server. This will restart al the vault servers if already installed.

```bash
ansible-playbook playbook.yml --tags vault
```
