# CLAUDE-INFRA.md

Infrastructure and wider-stack inventory. Read on demand — only when a task touches infrastructure, provisioning, ERP, or external data sources. Day-to-day coding conventions live in `CLAUDE-COMMON.md`.

## Infrastructure

- **Virtualization**: Proxmox — services run on Ubuntu LTS VMs. Windows Server 2016/2025 Standard VMs handle Active Directory.
- **Automation/provisioning**: Ansible, executed from a Linux Ansible Workstation.
- **Containers**: Docker Compose for containerized deployments.
- **Production topology**: Gunicorn behind Nginx.

## Network

- **Split-horizon DNS**: `*.apps.smtw.in` (e.g. `timescaledb.apps.smtw.in`, `kbs.apps.smtw.in`) is an
  internal zone. It resolves to 10.24.x.x only through the on-prem resolvers. When the laptop's adapter
  picks up a public DNS server (1.1.1.1), every internal name fails with "DNS name does not exist";
  database logins and Keycloak JWKS fetches then fail and look like app faults. Fix: `ipconfig /renew`;
  check with `Resolve-DnsName timescaledb.apps.smtw.in` (must return 10.24.x.x).
- **Keycloak from LAN servers**: `https://sso.mspv.app` (realm `Office.smtw.in`) resolves to a public
  IP that the LAN app servers (10.24.0.0/23) cannot reach. Keycloak runs at `kbs.apps.smtw.in` =
  10.24.0.119, plain HTTP on :8080 behind nginx, so every backend on a LAN server sets
  `KEYCLOAK_HOST_IP=10.24.0.119` (pattern: SMTW-WebApp-Base § Keycloak Token Validation Pattern).
  Without it the JWKS fetch times out and the SPA shows a misleading "no role assigned"; it still
  works on the laptop, which has internet access.

## ERP

- **Frappe / ERPNext** apps for ERP functionality.

## External data sources

- **MS SQL** — read-only source systems (queried, never written to).

## Desktop

- **Python GUI** frameworks when a desktop tool is needed.