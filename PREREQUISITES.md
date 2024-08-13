# Prerequisites

Make sure you have the following pre-steps completed before you start the deployment.

Look for the word `TODO` in the file, and change the value to your value.

## Tools and Services

* [Python 3.10](https://www.python.org/downloads/release/python-3100/) or higher installed
  * [Poetry - PYTHON PACKAGING AND DEPENDENCY MANAGEMENT MADE EASY](https://python-poetry.org/)
* [Terraform](https://www.terraform.io/) installed

## [Inventory File](inventory.yml)

This any change in this file will cause the entire infrastructure to be recreated.

Create a YAML file `inventory.yml`.

Make sure the `plugin`  is set to `vault_inventory_builder`.

```yaml
---
plugin: vault_inventory_builder
vaultops_tmp_dir_path: # TODO: The temporary directory path., Type: str
storage_config: # TODO: To store vault snapshot and terraform state, Type: str (Path to the file) | Dict: Actual Storage configuration
vault_config: # TODO: Location of the vault configuration file, Type: str (Path to the file) | Dict: Actual Vault configuration
```

* You can change this file in [ansible.cfg](ansible.cfg#L2) file.

```ini
[defaults]
inventory = inventory.yml
```

## Storage Configuration

Storage for terraform state and vault snapshot.

```yaml
type: # TODO: The type of the storage, Type: str, Options: [s3, local]
option: # TODO: The storage configuration, Type: Dict[Str, Any]
```

### Option: local

```yaml
---
type: local
option:
    path: # TODO: The path of the local storage, Type: str
```

### Option: S3

```yaml
---
type: s3
option:
    vaultops_s3_aes256_sse_customer_key_base64: # TODO: The base64 encoded AES256 key, Type: str
    vaultops_s3_bucket_name: # TODO: The name of the bucket, Type: str
    vaultops_s3_endpoint_url: # TODO: The endpoint URL of the bucket, Type: str
    vaultops_s3_access_key: # TODO: The access key of the bucket, Type: str
    vaultops_s3_secret_key: # TODO: The secret key of the bucket, Type: str
    vaultops_s3_signature_version: # TODO: The signature version of the bucket, Type: str, Default: s3v4
    vaultops_s3_region: # TODO: The region of the bucket, Type: str
```

## Vault Config

vault_config is a dictionary that contains the configuration of the vault , secrets and ansible inventory.

```yaml
vault_servers: # TODO: The servers of the vault cluster, Type: Dict[Str, Dict]
vault_secrets: # TODO: The secrets of the vault cluster, Type: Dict[Str, Any]
```

### Vault Servers, Nodes

It's mandatory to use TLS and mTLS for Vault because Vault is a secrets management tool,
and using it without TLS and mTLS is not secure.
Cloud IP addresses are not allowed, because they can change.

Vault node id will be `<server-name>-<node-name>`, for example, server1-node1, server1-node2, server2-node1,
server2-node2 and so on.

for the following example I have 2 servers, server1 and server2, each server has 2 nodes, node1 and node2.
`server-name` is `server1` and `server2`, `node-name` is `node1` and `node2`.

```yaml
---
vault_servers:
    server1: # TODO: The name of the server, this is `server-name`, Type: Dict[Str, Dict]
        root_ca_key_pem_as_ansible_priv_ssh_key: true # TODO: The root CA key will be used as ansible private ssh key, Type: bool, Default: True
        host_keys: # TODO: The host keys of the server, Type: List[Str]
            - ssh-ed25519 AAAAC3NzaC1... # TODO: The host key of the server, Type: str
            - ssh-rsa AAAAB3NzaC1yc2EAAAADAQA... # TODO: The host key of the server, Type: str
            - ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoY.... # TODO: The host key of the server, Type: str
        ansible_opts: # TODO: The ansible options for the server, Type: Dict[Str, Any]
            ansible_user: # TODO: The user to connect to the server, Type: str
            ansible_host: # TODO: The way to connect to the server, IP address or FQDN, Type: str
            ansible_ssh_host: # TODO: The way to connect to the server, IP address or FQDN, Type: str
        cluster_addr_fqdn: # TODO: The way to connect to vault cluster FQDN, Type: str
        cluster_ip: # TODO: The way to connect to vault cluster, IP address, Type: str
        api_addr_fqdn: # TODO: The way to connect to vault API, FQDN, Type: str
        api_ip: # TODO: The way to connect to vault API, IP address, Type: str
        vault_nodes: # TODO: The nodes of the vault cluster. Type: Dict[Str, Any]
            node1: # TODO: The name of the node, this is `node-name`, Type: Dict[Str, Any]
                node_port: 8200 # TODO: The port of the node, Type: int
                cluster_port: 8201 # TODO: The port of the cluster, Type: int
                cluster_addr_fqdn: # TODO: The way to connect to vault cluster FQDN, Type: str
                cluster_ip: # TODO: The way to connect to vault cluster, IP address, Type: str
                api_addr_fqdn: # TODO: The way to connect to vault API, FQDN, Type: str
                api_ip: # TODO: The way to connect to vault API, IP address, Type: str
                explicit_retry_join_nodes: # TODO: Node ids of the nodes to join the cluster, if `explicit_retry_join_nodes` is declared and no node is available, then no `retry_join` will be used, Type: Dict[Str, Any]
                    server1-node2: null # TODO: The node id of the node, this is `server-name-node-name` Type: Dict[Str, Any]
                    server2-node1: null # TODO: The node id of the node, this is `server-name-node-name` Type: Dict[Str, Any]
            node2: # TODO: The name of the node, this is `node-name` Type: Dict[Str, Any]
                node_port: 8202 # TODO: The port of the node, Type: int
                cluster_port: 8203 # TODO: The port of the cluster, Type: int
```

Priority of the `cluster_ip` and `api_ip` is higher than `cluster_addr_fqdn` and `api_addr_fqdn`. These options will
be used instead of the server level if they are set on the `vault_node` level.

### Secrets

```yaml
---
vault_secrets:
    vault_ha_hostname: localhost # TODO: The way to connect to vault cluster, IP address or FQDN, Type: str
    vault_ha_port: 8200 # TODO: The port of the cluster, Type: int
    bot_gpg_key:
        BOT_GPG_PRIVATE_KEY: # TODO: The private key of the GPG key, Type: str
        BOT_GPG_PASSPHRASE: # TODO: The passphrase of the GPG key, Type: str
    github_details:
        github_bot:
            GH_BOT_API_TOKEN: # TODO: The GitHub API token of the bot, Type: str
        github_prod:
            GH_PROD_API_TOKEN: # TODO: The GitHub API token of the production, Type: str
        root_pki_details:
            root_ca_key_password: # TODO: The password of the root CA key, Type: str
            root_ca_key_pem: # TODO: The root CA key in PEM format, Type: str
            root_ca_cert_pem: # TODO: The root CA certificate in PEM format, Type: str
        vault_admin_userpass_details:
            vault_admin_user: # TODO: The admin user of the vault, Type: str
            vault_admin_password: # TODO: The admin password of the vault, Type: str
            vault_admin_userpass_mount_path: # TODO: The mount path of the userpass, Type: str
            vault_admin_policy_name: # TODO: The policy name of the admin, Type: str
            vault_admin_client_cert_p12_passphrase: # TODO: The passphrase of the client certificate, Type: str
        external_services: # TODO: The external services of the vault, this will be uploaded to secret/data/external_services, Type: Dict[Str, Any]
        ansible_inventory: # TODO: The external services of the vault, this will be uploaded to secret/data/external_services, Type: Dict[Str, Any]
            vars:
            children:
            hosts:   
```

## Export Requirements

```bash
poetry export --without-hashes --format=requirements.txt --with dev > .github/files/requirements.txt
```
