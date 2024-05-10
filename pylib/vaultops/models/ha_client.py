import base64
from typing import Optional

import hvac  # type: ignore
import requests
import yaml
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr
from requests.sessions import HTTPAdapter
from urllib3 import Retry

from ..models.vault_config import VaultConfig


class VaultHaClient(BaseModel):
    """
    Represents a client for interacting with HashiCorp Vault in a high-availability (HA) setup.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    _vault_client: Optional[hvac.Client] = None
    admin_user: str = Field(default=...)
    admin_password: str = Field(default=...)
    userpass_mount: str = Field(default=...)
    policy_name: str = Field(default=...)
    client_cert_pem: str = Field(default=...)
    client_key_pem: str = Field(default=...)
    vault_ha_hostname: str = Field(default=...)
    vault_ha_port: int = Field(default=...)
    client_cert_p12_base64: str = Field(default=...)
    client_cert_p12_passphrase: str = Field(default=...)
    root_ca_cert_pem: str = Field(default=...)

    vault_root_ca_cert_file: Optional[str] = Field(default=None)
    vault_client_cert_file: Optional[str] = Field(default=None)
    vault_client_key_file: Optional[str] = Field(default=None)
    _hvac_client: hvac.Client = PrivateAttr()

    def __init__(self, vault_config: Optional[VaultConfig] = None, **data):
        super().__init__(**data)
        if not vault_config:
            return
        with open(f"{vault_config.vaultops_tmp_dir_path}/vault-ha-client.yml", "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False)

        self.vault_root_ca_cert_file = f"{vault_config.vaultops_tmp_dir_path}/vault-ha-root-ca.pem"
        self.vault_client_cert_file = f"{vault_config.vaultops_tmp_dir_path}/vault-ha-client-cert.pem"
        self.vault_client_key_file = f"{vault_config.vaultops_tmp_dir_path}/vault-ha-client-priv.key"

        with open(self.vault_root_ca_cert_file, "w", encoding="utf-8") as f:
            f.write(self.root_ca_cert_pem)

        with open(self.vault_client_cert_file, "w", encoding="utf-8") as f:
            f.write(self.client_cert_pem)

        with open(self.vault_client_key_file, "w", encoding="utf-8") as f:
            f.write(self.client_key_pem)

        with open(f"{vault_config.vaultops_tmp_dir_path}/vault-ha-client-cert.p12", "wb") as f:
            f.write(base64.b64decode(self.client_cert_p12_base64))

        adapter = HTTPAdapter(max_retries=Retry(total=2, backoff_factor=2))
        session = requests.Session()
        session.verify = self.vault_root_ca_cert_file
        session.cert = (self.vault_client_cert_file, self.vault_client_key_file)
        session.mount("https://", adapter)
        hvac_client = hvac.Client(url=f"https://{self.vault_ha_hostname}:{self.vault_ha_port}", session=session)
        self._hvac_client = hvac_client

    def hvac_client(self) -> hvac.Client:
        """
        Returns the hvac client object
        """
        if not self._hvac_client.is_authenticated():
            self._hvac_client.auth.userpass.login(
                username=self.admin_user, password=self.admin_password, mount_point=self.userpass_mount
            )
        return self._hvac_client
