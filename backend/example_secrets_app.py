"""Template for secrets_app.py — copy to secrets_app.py (gitignored) and fill in.

The defaults below match the local dev DB (tooling/dev/docker-compose.dev.yml).
In production secrets_app.py is rendered by Ansible
(smtw_erp_devops/erp_server/yantra/secrets_app.py.j2) and mounted read-only.
"""

# Flask
SECRET_KEY = "CHANGE_ME"

# MariaDB
DB_HOST = "127.0.0.1"
DB_PORT = 3307
DB_USER = "vel_yantra_master"
DB_PASSWORD = "dev-password"
DB_NAME = "vel_yantra_master"

# Keycloak — full realm URL (base URL + /realms/ + realm name)
KEYCLOAK_REALM_URL = "https://sso.mspv.app/realms/Office.smtw.in"
KEYCLOAK_CLIENT_ID = "vel-yantra-master"
# LAN IP for backend→Keycloak JWKS calls (bypasses DNS/proxy).
# _make_internal_url() rewrites the realm URL to http://{IP}:8080/...
# Leave "" if the backend can reach the Keycloak URL directly.
KEYCLOAK_HOST_IP = ""

# Role used by DEV_AUTH_BYPASS=1 (dev only). Change to test as a non-admin.
# "admin" or "it_admin": a token role, at every site.  A site role ("maint_engineer", ...):
# that role at every site, all units.  "maintenance_team": logged in with no access, to see
# the "no access yet" page (S011 § 5.8).
# DEV_STUB_ROLE = "admin"
