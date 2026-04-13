
output "storage_account_name" {
  description = "The name of the storage account for tfstate."
  value       = azurerm_storage_account.tfstate.name
}

output "storage_container_name" {
  description = "The name of the storage container for tfstate."
  value       = azurerm_storage_container.tfstate.name
}

output "resource_group_name" {
  description = "The name of the resource group for tfstate."
  value       = azurerm_resource_group.tfstate.name
}
