# Proposal for SMTW-WebApp-Base.md — MariaDB lock names carry the database name

For the user to paste into `smtw-common` (the synced `.claude/SMTW-WebApp-Base.md` is not edited here). Source: finding CR1-09 of `2026-10-22-test-isolation-review.md`.

**Where:** § Singleton via DB lock (line 436), after the code example and the paragraph that ends "...released automatically if its process dies."

**Text to add:**

> **MariaDB lock names are server-wide: put the database name in them.** `GET_LOCK` names belong to the whole server, not to one database. Two apps, two environments (production and test), or two parallel test databases that share one server and use the same name `appname_migrations` wait on each other. A second database on the server then never gets its own worker or migration lock.
>
> - Build every lock name in one helper: `f"{base}:{database}"`, e.g. `appname_migrations:vel_appname_master`. Check the length in the helper: MariaDB allows 64 characters and refuses a longer name with an error.
> - Use that helper at every `GET_LOCK` / `RELEASE_LOCK` / `IS_USED_LOCK` call, and in tests that hold a lock. Do not write the literal name at a call site.
> - Test databases are named per run and per parallel worker (`vel_appname_test_<run>_<worker>`), so a test lock that carries the database name never collides across workers or runs.
> - Reference: Yantra `backend/local_db.py` (`named_lock`) and `backend/tests/db_names.py`.
> - PostgreSQL advisory locks use numeric keys per database, so this does not apply there.
