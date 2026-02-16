
variable "resource_group_name" {
  description = "Name of the resource group for storing tfstate."
  type        = string
  default     = "tfstate-rg"
}

variable "location" {
  description = "Azure region for the tfstate resources."
  type        = string
  default     = "West Europe"
}

variable "storage_account_prefix" {
  description = "Prefix for the storage account name."
  type        = string
  default     = "tfstate"
}

variable "storage_container_name" {
  description = "Name of the blob container for tfstate."
  type        = string
  default     = "tfstate"
}

variable "tags" {
  description = "A map of tags to add to all resources."
  type        = map(string)
  default = {
    "environment" = "bootstrap"
    "terraform"   = "true"
  }
}
