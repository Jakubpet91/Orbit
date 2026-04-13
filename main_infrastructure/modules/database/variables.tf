variable "db_server_name" {
  description = "The name of the PostgreSQL server."
  type        = string
}

variable "resource_group_name" {
  description = "The name of the resource group in which to create the server."
  type        = string
}

variable "location" {
  description = "The Azure region where the server will be created."
  type        = string
}

variable "delegated_subnet_id" {
  description = "The ID of the subnet delegated to the PostgreSQL server."
  type        = string
}

variable "private_dns_zone_id" {
  description = "The ID of the private DNS zone to use for the PostgreSQL server."
  type        = string
}

variable "administrator_login" {
  description = "The administrator login for the PostgreSQL server."
  type        = string
}

variable "administrator_password" {
  description = "The administrator password for the PostgreSQL server."
  type        = string
  sensitive   = true
}

variable "sku_name" {
  description = "The SKU name for the PostgreSQL server."
  type        = string
  default     = "B_Standard_B1ms" # Burstable B1ms tier
}

variable "tags" {
  description = "A map of tags to add to all resources."
  type        = map(string)
  default     = {}
}
