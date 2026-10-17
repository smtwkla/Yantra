# Keycloak setup for Yantra

The reference for setting up and maintaining Yantra's login in Keycloak: the
client, the roles, the users, and the change of roles that S011 brings.
Yantra's code reads these settings; it never changes anything in Keycloak.

Sources: `docs/Plan.MD` § 1 and § 3 (decisions), `backend/auth_utils.py` (what
the code reads from a token), `frontend/src/stores/auth.js` (how the browser
logs in), S011 brief § 5.7 (the switch-over).

## 1. Realm and client

| Setting | Value |
|---|---|
| Keycloak | `https://sso.mspv.app` |
| Realm | `Office.smtw.in` |
| Client ID | `vel-yantra-master` |
| Client type | OpenID Connect, **public** (no client secret: the browser logs in) |
| Client authentication | Off |
| Authentication flow | **Standard flow** only. Direct access grants, implicit flow and service accounts off |
| PKCE | Required, method **S256** (Advanced › Proof Key for Code Exchange) |
| Root / home URL | `https://vel-yantra.mspv.app` |
| Valid redirect URIs | `https://vel-yantra.mspv.app/*` |
| Valid post logout redirect URIs | `https://vel-yantra.mspv.app/*` (logout returns to the app) |
| Web origins | `https://vel-yantra.mspv.app` (lets the browser call the token endpoint) |
| Front-channel logout | On (default) |

**What the token must carry** (the defaults do this; check them if login
fails with "no role"):
- `preferred_username` and `name` (client scope `profile`, default);
- realm roles in `realm_access.roles` and client roles in
  `resource_access.vel-yantra-master.roles` (client scope `roles`, default,
  with its "realm roles" and "client roles" mappers).

The backend checks the token's signature against the realm's keys, its
expiry, and that `azp` (authorized party) is `vel-yantra-master`. It does not
check `aud`.

**Development.** The dev backend normally runs with `DEV_AUTH_BYPASS=1` and
never contacts Keycloak. To test real login locally, add
`http://localhost:5176/*` to the redirect and post-logout URIs and
`http://localhost:5176` to the web origins, and remove them afterwards.

## 2. Settings Yantra needs (deployment)

Rendered by Ansible into `secrets_app.py` (`smtw_erp_devops/erp_server/yantra/secrets_app.py.j2`);
field names as in `backend/example_secrets_app.py`:

| Field | Value |
|---|---|
| `KEYCLOAK_REALM_URL` | `https://sso.mspv.app/realms/Office.smtw.in` |
| `KEYCLOAK_CLIENT_ID` | `vel-yantra-master` |
| `KEYCLOAK_HOST_IP` | optional: Keycloak's LAN IP, so the backend fetches the realm's keys over the LAN (`http://<ip>:8080`) instead of through the public proxy |

`GET https://vel-yantra.mspv.app/api/auth/config` shows what the running
backend uses (public, no login). A changed `secrets_app.py` takes effect only
after the backend is recreated; the deploy does that since S007.

## 3. Roles

### 3.1 Today (until S011 is deployed)

Client roles on `vel-yantra-master`; a user may hold several and gets the
union. They apply at **every** site.

| Client role | Who |
|---|---|
| `maint_operator` | Equipment operators |
| `maint_technician` | Maintenance technicians |
| `maint_engineer` | Maintenance engineers |
| `maint_manager` | Maintenance manager |
| `maint_storekeeper` | Maintenance stores |
| `it_admin` | IT: masters housekeeping, user access, settings |

Realm role **`mspv-apps-admin`** (org-wide, or a realm role `admin`) = Yantra's
**admin**: every permission, bypassing all checks.

### 3.2 After S011 (roles per site, held in Yantra)

Keycloak only says who may log in and who is IT admin:

| Role | Kind | Meaning |
|---|---|---|
| `maintenance_team` | client role | May log in. Grants **nothing** by itself: what the user may do, and where, is set in Yantra › Masters › **Team**, on the person whose login is this username (one role per site, plus units) |
| `it_admin` | client role | IT admin, at every site, as today |
| `mspv-apps-admin` | realm role | Admin, as today |

The five `maint_*` roles are then **ignored** by Yantra (Yantra also has a sixth site
role, `maint_supervisor`, that never existed in Keycloak) (the backend logs a
warning while a user still carries them). A user with none of the three roles
above gets "Your account is not in the maintenance team" (401).

A **group** makes this easy: e.g. group `Yantra maintenance` with client role
`maintenance_team`; put every maintenance user in it.

## 4. Roles to create and delete

### Now (before S011)
- **Create** client role `maintenance_team` on `vel-yantra-master`, and give
  it to every maintenance user (through the group). Harmless today: the
  current code ignores roles it doesn't know.
- **Keep** `it_admin` and the five `maint_*` roles: the running release still
  reads them.
- **Delete nothing yet.**
- **Check:** if an old client `vel-yantra` (without `-master`) still exists and
  nothing uses it, it can be deleted. Yantra uses only `vel-yantra-master`.

### After S011 is deployed (S011 brief § 5.7)
1. (Done above) every maintenance user has `maintenance_team`.
2. Deploy S011. Users log in and see "You have no access yet" until step 3.
3. IT admin enters each user's sites and roles in Yantra › Masters › **Team**:
   open the person (migration v8 created one per old unit-access username, named
   after the username, with its units already shown and no role), give each site
   a role and save. A person with no Team record is added there with their login.
   Engineers can add Technicians at their own site.
4. Once every user has access **and** a rollback to the previous release is no
   longer wanted, **delete** the client roles `maint_operator`,
   `maint_technician`, `maint_engineer`, `maint_manager`, `maint_storekeeper`
   (the old release needs them). The backend's warning lines show who still
   carries them.

`it_admin` and `maintenance_team` stay for good.

## 5. Usernames

- Yantra identifies people by `preferred_username`, compared in lower case.
- Logins typed into Yantra (Team › login, S010 A1; IT admin only) are **not
  checked** against Keycloak (user, 16-10-2026): copy the username exactly as
  Keycloak shows it. A typo just never matches.
- **Team › login is IT admin's only** (S010 A1): engineers see only whether a
  person has a login. Deactivating or reactivating a person who has a login is
  IT admin's too, and nobody can set their own login (ISO 27001 A.5.3, A.8.2).
- **AD users:** the realm's LDAP federation maps the AD attribute
  **`userPrincipalName`** to the Keycloak username (user, 16-10-2026), so an AD
  user's login in Yantra is their UPN, e.g. `kla@office.smtw.in` (lower case).
  Keycloak admin › Users shows it in the Username column. In Yantra, the
  Team dialog shows IT admin's own login under the Login field as an example.
- **Local users** (operators, § 6) follow
  one scheme that can't clash with AD: preferably the OneERP employee number,
  e.g. `E1042`.

## 6. Shared-device login (kiosks; decided 13-10-2026)

Operators are Keycloak **local users** in `Office.smtw.in` with passwords: no
AD account, so no CAL; no PINs, RFID or badges exist. Kiosks are not in v1, but
these settings apply to local users from the start.

- **Logout ends the Keycloak session too** (OIDC RP-initiated logout), both on
  manual logout and on inactivity timeout. Clearing only Yantra's token would
  leave the Keycloak cookie in the kiosk browser and sign the next person in as
  the previous one. The kiosk browser saves no passwords; **"Remember me" is
  off** (realm › Login).
- The screen always shows **who is logged in**, with a large logout button, so
  a forgotten session is noticed by the next person.
- **Password policy** (realm-wide, Authentication › Policies) per NIST SP
  800-63B: minimum 8 characters, checked against breached-password lists, no
  forced complexity or periodic change.
- **Brute-force protection** on (realm › Security defenses), with a
  **temporary** lockout (e.g. 15 min), so nobody can lock a colleague out for
  good from a shared kiosk.
- **Joiners and leavers** (ISO 27001 A.5.18): local users are not in AD, so
  disabling someone in AD does not disable them; the Keycloak user is disabled
  by hand when an operator leaves. After S011, also **deactivate the person** in
  Yantra › Masters › Team (IT admin), which ends their Yantra access at once.
- Accounts and password resets are IT's job in Keycloak, outside Yantra; Yantra
  stores no passwords.
- Inactivity timeout: start at about 5 minutes on kiosks (OWASP suggests 2–5
  min for shared devices); tune when kiosks arrive.

## 7. Checking a login problem

| Symptom | Likely cause |
|---|---|
| Keycloak page "Client not found" | The backend's client ID differs from Keycloak's: check `/api/auth/config`; recreate the backend after a `secrets_app.py` change |
| "Invalid redirect uri" | § 1 redirect URIs / web origins don't match the address used |
| Signed in, then "no role" / "not in the maintenance team" | The user lacks the roles of § 3 (today: a `maint_*` or `it_admin`; after S011: `maintenance_team` or `it_admin`) |
| After S011: "You have no access yet" | No site role on their person in Yantra › Masters › Team, no person with that login, or the person is inactive. Ask IT or the site's engineer |
| Logout, and the next person is signed in as the previous one | Post-logout redirect URI missing, or "Remember me" on |
