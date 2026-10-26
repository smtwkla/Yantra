# What changed in Yantra

## 0.1.11 — 26-10-2026
- Sign-in is stricter. Yantra accepts only correctly signed tokens (RS256) from the expected login server, and it allows 30 seconds of clock difference.
- If the login server (Keycloak) is down, Yantra now says so with a clear "login server down" answer (503) instead of a general error.
- A bad sign-in token is no longer retried. The login server key is fetched with a 5-second limit, so a slow login server no longer holds up the app.
- Development sign-in bypass (`DEV_AUTH_BYPASS`) is now refused outside debug mode.
- Production no longer sends the wrong `Access-Control-Allow-Origin: http://localhost:5176` header. The unused `flask-cors` library is removed, because the app is served from one address behind Nginx.
- A change log is now available. IT Admin and Admin can open it by clicking the version in the sidebar. Each release adds its own section.

## 0.1.10 — 25-10-2026
- Anyone in the plant can raise a ticket for a breakdown, a defect or an early sign.
- Engineers can defer a ticket, put it on hold with a date to check it again, and work it through to closing.
- The Me page shows a person's open work, the tickets they raised and their own activity.
- Yantra sends an alert to the phone when a ticket needs attention, and the site managers get an email when a ticket is closed.
- Each machine in the equipment list has its parts, photos, documents, nameplate values and a QR label to print.
- Operators can add meters to a machine and log a reading from the machine's page.
- The Readings screen lists all the meters of a site, one row per meter, so the day's readings can be logged together.
- IT Admin sets the masters (sites, units, machine classes, meter types) and the team, with each person's roles per site.
