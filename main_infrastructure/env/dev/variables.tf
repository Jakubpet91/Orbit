# Common variables
variable "resource_group_name" {
  description = "The name of the main resource group."
  type        = string
  default     = "orbit-dev-rg"
}

variable "location" {
  description = "The Azure region for all resources."
  type        = string
  default     = "WestEurope"
}

variable "tags" {
  description = "A map of tags to add to all resources."
  type        = map(string)
  default = {
    "Environment" = "Dev"
    "Project"     = "Orbit"
  }
}

# Network variables
variable "vnet_name" {
  description = "The name of the virtual network."
  type        = string
  default     = "orbit-dev-vnet"
}

variable "vnet_address_space" {
  description = "The address space for the virtual network."
  type        = list(string)
  default     = ["10.0.0.0/16"]
}

variable "backend_subnet_name" {
  description = "The name of the backend subnet."
  type        = string
  default     = "backend-subnet"
}

variable "backend_subnet_address_prefix" {
  description = "The address prefix for the backend subnet."
  type        = string
  default     = "10.0.1.0/24"
}

variable "db_subnet_name" {
  description = "The name of the database subnet."
  type        = string
  default     = "db-subnet"
}

variable "db_subnet_address_prefix" {
  description = "The address prefix for the database subnet."
  type        = string
  default     = "10.0.2.0/24"
}

# AKS variables
variable "aks_cluster_name" {
  description = "The name of the AKS cluster."
  type        = string
  default     = "orbit-dev-aks"
}

variable "aks_dns_prefix" {
  description = "The DNS prefix for the AKS cluster."
  type        = string
  default     = "orbit-dev-aks"
}

variable "aks_vm_size" {
  description = "The size of the virtual machines to use for the nodes."
  type        = string
  default     = "Standard_C2s"
}

variable "aks_node_count" {
  description = "The number of nodes in the node pool."
  type        = number
  default     = 4
}

# Database variables
variable "db_server_name" {
  description = "The name of the PostgreSQL server."
  type        = string
  default     = "orbit-dev-db"
}

variable "db_administrator_login" {
  description = "The administrator login for the PostgreSQL server."
  type        = string
}

variable "db_administrator_password" {
  description = "The administrator password for the PostgreSQL server."
  type        = string
  sensitive   = true
}

variable "db_sku_name" {
  description = "The SKU name for the PostgreSQL server."
  type        = string
  default     = "B_Standard_B1ms"
}
