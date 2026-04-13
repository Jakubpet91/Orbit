variable "resource_group_name" {
  description = "The name of the resource group in which to create the network resources."
  type        = string
}

variable "location" {
  description = "The Azure region where the network resources will be created."
  type        = string
}

variable "vnet_name" {
  description = "The name of the virtual network."
  type        = string
  default     = "spoke1-vnet"
}

variable "vnet_address_space" {
  description = "The address space for the virtual network."
  type        = list(string)
  default     = ["10.1.0.0/16"]
}

variable "backend_subnet_name" {
  description = "The name of the backend subnet."
  type        = string
  default     = "backend-subnet"
}

variable "backend_subnet_address_prefix" {
  description = "The address prefix for the backend subnet."
  type        = string
  default     = "10.1.1.0/24"
}

variable "db_subnet_name" {
  description = "The name of the database subnet."
  type        = string
  default     = "db-subnet"
}

variable "db_subnet_address_prefix" {
  description = "The address prefix for the database subnet."
  type        = string
  default     = "10.1.2.0/24"
}

variable "tags" {
  description = "A map of tags to add to all resources."
  type        = map(string)
  default     = {}
}