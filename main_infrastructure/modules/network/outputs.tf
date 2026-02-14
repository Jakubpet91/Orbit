
output "vnet_id" {
  description = "The ID of the virtual network."
  value       = azurerm_virtual_network.main.id
}

output "backend_subnet_id" {
  description = "The ID of the backend subnet."
  value       = azurerm_subnet.backend.id
}

output "db_subnet_id" {
  description = "The ID of the database subnet."
  value       = azurerm_subnet.database.id
}

output "vnet_name" {
  description = "The name of the virtual network."
  value       = azurerm_virtual_network.main.name
}

output "backend_subnet_name" {
  description = "The name of the backend subnet."
  value       = azurerm_subnet.backend.name
}

output "postgres_private_dns_zone_id" {
  description = "The ID of the private DNS zone for PostgreSQL."
  value       = azurerm_private_dns_zone.postgres.id
}
