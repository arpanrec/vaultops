# pylint: disable=C0114
from typing import Any, Dict, Optional

import requests
import yaml
from packaging.version import Version

sha_dict = {
    "cs_hashicorp_vault_info_map": {
        "x86_64": {"vault_arch": "amd64", "sha256sum": {}},
        "aarch64": {"vault_arch": "arm64", "sha256sum": {}},
    }
}
__vault_releases_url: str = "https://releases.hashicorp.com/vault/index.json"
_vault_releases: Dict[str, Any] = requests.get(__vault_releases_url, timeout=10).json()["versions"]
# https://releases.hashicorp.com/vault/1.18.2/vault_1.18.2_SHA256SUMS
_expected_version: Optional[str] = None
for key in list(_vault_releases.keys()):
    print(f"Processing {key}")
    if ("+" in key) or ("beta" in key) or ("rc" in key) or ("oci" in key) or ("alpha" in key):
        continue
    sha_file_content = requests.get(
        f"https://releases.hashicorp.com/vault/{key}/vault_{key}_SHA256SUMS", timeout=10
    ).text
    for line in sha_file_content.split("\n"):
        if "linux_amd64" in line:
            sha_dict["cs_hashicorp_vault_info_map"]["x86_64"]["sha256sum"][key] = line.split()[0]  # type: ignore
        elif "linux_arm64" in line:
            sha_dict["cs_hashicorp_vault_info_map"]["aarch64"]["sha256sum"][key] = line.split()[0]  # type: ignore
    if not _expected_version:
        _expected_version = key
    else:
        if Version(key) > Version(_expected_version):
            _expected_version = key

print(f"Latest Vault release tag: {_expected_version}")
with open("foo-data.yml", "w", encoding="utf-8") as outfile:
    yaml.dump(sha_dict, outfile, default_flow_style=False)
