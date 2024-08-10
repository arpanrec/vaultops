locals {
  codified_vault_addr = format("%s://%s:%s",
    var.codifiedvault_protocol,
    var.codifiedvault_vault_fqdn,
  var.codifiedvault_vault_port)
}
