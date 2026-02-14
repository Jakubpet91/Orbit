variable "cluster_name" {
  description = "The name of the AKS cluster."
  type        = string
}

variable "location" {
  description = "The Azure region where the AKS cluster will be created."
  type        = string
}

variable "resource_group_name" {
  description = "The name of the resource group in which to create the AKS cluster."
  type        = string
}

variable "dns_prefix" {
  description = "The DNS prefix for the AKS cluster."
  type        = string
}

variable "vm_size" {
  description = "The size of the virtual machines to use for the nodes."
  type        = string
  default     = "Standard_B2s"
}

variable "node_count" {
  description = "The number of nodes in the node pool."
  type        = number
  default     = 1
}

variable "vnet_subnet_id" {
  description = "The subnet ID for the AKS cluster."
  type        = string
}

variable "tags" {
  description = "A map of tags to add to all resources."
  type        = map(string)
  default     = {}
}