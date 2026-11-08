terraform {
  required_version = ">= 1.6.0"

  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.120.0"
    }
  }
}

provider "proxmox" {
  endpoint  = var.pm_api_url
  api_token = "${var.pm_api_token_id}=${var.pm_api_token_secret}"
  insecure  = true
}

variable "pm_api_url" {
  type = string
}

variable "pm_api_token_id" {
  type = string
}

variable "pm_api_token_secret" {
  type      = string
  sensitive = true
}

variable "proxmox_node_name" {
  type    = string
  default = "proxmox"
}

data "proxmox_vm" "db_server" {
  node_name = var.proxmox_node_name
  id        = 100
}

data "proxmox_vm" "app_server" {
  node_name = var.proxmox_node_name
  id        = 102
}

resource "terraform_data" "lab6_inventory" {
  input = {
    db_server = {
      vm_id  = data.proxmox_vm.db_server.id
      name   = data.proxmox_vm.db_server.name
      status = data.proxmox_vm.db_server.status
    }
    app_server = {
      vm_id  = data.proxmox_vm.app_server.id
      name   = data.proxmox_vm.app_server.name
      status = data.proxmox_vm.app_server.status
    }
  }
}

output "db_server" {
  value = terraform_data.lab6_inventory.output.db_server
}

output "app_server" {
  value = terraform_data.lab6_inventory.output.app_server
}
