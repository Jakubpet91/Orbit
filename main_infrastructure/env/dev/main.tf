terraform {
  backend "azurerm" {
    # This will be configured via CLI arguments in the CI/CD pipeline
  }
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

module "network" {
  source = "../../modules/network"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tags                = var.tags

  vnet_name                     = var.vnet_name
  vnet_address_space            = var.vnet_address_space
  backend_subnet_name           = var.backend_subnet_name
  backend_subnet_address_prefix = var.backend_subnet_address_prefix
  db_subnet_name                = var.db_subnet_name
  db_subnet_address_prefix      = var.db_subnet_address_prefix
}

module "aks" {
  source = "../../modules/aks"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tags                = var.tags

  cluster_name   = var.aks_cluster_name
  dns_prefix     = var.aks_dns_prefix
  vm_size        = var.aks_vm_size
  node_count     = var.aks_node_count
  vnet_subnet_id = module.network.backend_subnet_id
}

module "database" {
  source = "../../modules/database"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tags                = var.tags

  db_server_name         = var.db_server_name
  delegated_subnet_id    = module.network.db_subnet_id
  private_dns_zone_id    = module.network.postgres_private_dns_zone_id
  administrator_login    = var.db_administrator_login
  administrator_password = var.db_administrator_password
  sku_name               = var.db_sku_name
}
