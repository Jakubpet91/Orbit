output "db_server_id" {
  description = "The ID of the PostgreSQL server."
  value       = azurerm_postgresql_flexible_server.db.id
}

output "db_server_name" {
  description = "The name of the PostgreSQL server."
  value       = azurerm_postgresql_flexible_server.db.name
}

output "db_server_fqdn" {
  description = "The FQDN of the PostgreSQL server."
  value       = azurerm_postgresql_flexible_server.db.fqdn
}
