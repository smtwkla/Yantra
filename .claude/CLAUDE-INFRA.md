# CLAUDE-INFRA.md

Infrastructure and wider-stack inventory. Read on demand — only when a task touches infrastructure, provisioning, ERP, or external data sources. Day-to-day coding conventions live in `CLAUDE-COMMON.md`.

## Infrastructure

- **Virtualization**: Proxmox — services run on Ubuntu LTS VMs. Windows Server 2016/2025 Standard VMs handle Active Directory.
- **Automation/provisioning**: Ansible, executed from a Linux Ansible Workstation.
- **Containers**: Docker Compose for containerized deployments.
- **Production topology**: Gunicorn behind Nginx.

## ERP

- **Frappe / ERPNext** apps for ERP functionality.

## External data sources

- **MS SQL** — read-only source systems (queried, never written to).

## Desktop

- **Python GUI** frameworks when a desktop tool is needed.