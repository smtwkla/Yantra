# SMTW Utils: Gallery app contract, version 1

Synced from smtw-common; edit it there.

This is what a repo puts in its `gallery/` folder so the gallery can publish it as an app. It is
written for the person (or Claude) building an app. Apps rely on this contract only, never on the
platform's internals (the Gallery repo's `docs/Gallery-Plan.md` § 2). The collector checks every rule in § 1–§ 4
before it publishes anything; the run-time rules in § 5 are yours to follow.

The constants below live in the Gallery repo's `collector/rules.py`; that file wins if the two ever differ.

## 1. Where an app lives

```
<your repo>/
  gallery/                 the folder the gallery reads (repos.toml can name another)
    bricks/                one app; the folder name is the app's slug
      gallery.toml         the manifest (§ 2)
      index.html           the entry page
      main.js, style.css, data/rates.csv, models/arch.glb, …
    README.md              a file directly in gallery/ is not an app: skipped, with a note
```

- The app is published at `/<key>/<slug>/`, where `<key>` is the repo's key in the gallery's
  `repos.toml` (e.g. `kiln`) and `<slug>` is the app's folder name (e.g. `bricks`).
- The app's folder name (its slug): 1–40 characters, lower-case letters, digits and `-`,
  starting with a letter (the same rule as a repo key, § 6). The file-name rules of § 3 apply
  to the folders and files inside the app, not to this name.
- **Only committed files are published.** The collector reads the commit that the branch (default
  `main`) points to in the local clone. Edits you have not committed, the index and untracked
  files are never read. Commit your app, then ask for a publish.
- Every folder under `gallery/` is an app and must have a `gallery.toml`.
- Any invalid app stops the whole publish: nothing is published until every app passes.

## 2. The manifest `gallery.toml`

```toml
contract    = 1                          # required; must be 1
title       = "Kiln bricks sandbox"      # required; 1–80 characters
description = "3D layout of the arch"    # optional; up to 300 characters
entry       = "index.html"               # optional; default "index.html"

[access]                                 # optional; omit it and every logged-in user can open the app
client = "vel-kiln-master"               # one Keycloak client id
roles  = ["manager", "operator"]         # that client's roles; any one of them opens the app
```

`[access]` is a TOML table, so it goes after the other keys. The inline form
`access = { client = "vel-kiln-master", roles = ["manager", "operator"] }` means the same.

| Key | Rule |
|---|---|
| `contract` | Required. The number `1` (not `"1"`, not `true`). |
| `title` | Required text, 1–80 characters after trimming spaces. One line: no line breaks or other control characters. |
| `description` | Optional text, up to 300 characters, one line. Default empty. |
| `entry` | Optional. The page the app opens on: one file in the app's own folder (no `/`), ending in `.html` or `.htm`, and one of the app's files. Default `index.html`. |
| `access` | Optional table with exactly two keys, `client` and `roles`. **Omit it** and every logged-in user can open the app. With it, only users who hold at least one of `roles` on `client` (and gallery admins) can. |
| `access.client` | Required in `[access]`. One Keycloak client id: 1–64 lower-case letters, digits, `_` or `-`, starting with a letter (`vel-kiln-master`). |
| `access.roles` | Required in `[access]`. A non-empty list of that client's role names, same characters as the client id (`kiln-incharge`), no duplicates. `roles = []` is an error. |

- **Any other key is an error**, at the top level and in `[access]`. A misspelt `acess` would
  otherwise open the app to everyone; a misspelt `role` would be ignored.
- **The roles are client roles**, the ones Keycloak shows under Clients → *client* → Roles.
  Realm roles never open an app, and a role of the same name on another client does not count.
  The names are compared exactly, capitals included. To find a client's roles, open the Keycloak
  admin console of the realm, then Clients → the client → the **Roles** tab; or ask the IT team.
- Roles that a user gets through a Keycloak group or from LDAP count like roles given directly.
- Gallery admins (the realm role `mspv-apps-admin`) open every app. A client role named `admin`
  does not make a gallery admin.
- The old form `access = ["group", …]` (Keycloak groups) is no longer read and is an error.
- The file must be UTF-8 TOML, at most 64 KB.
- `gallery.toml` itself is not published; its content goes into the gallery's `catalog.json`.

## 3. File names

Every file of the app (all but `gallery.toml`):

- **Each part of the path** (each folder name and the file name):
  - uses only `A–Z a–z 0–9 . _ -`;
  - starts with a letter or digit, so no dot files (`.env`, `.gitignore`);
  - does not end with `.` (Windows drops it);
  - is at most 100 characters;
  - is not a Windows device name (`CON`, `PRN`, `AUX`, `NUL`, `COM1`–`COM9`, `LPT1`–`LPT9`,
    with any extension: `con.txt` is out too).
- No spaces and no `%`: the name in the URL, on the server's disk and in git must be the same
  text, with no encoding.
- At most **8 levels** below the app folder and **120 characters** for the whole path below it.
- **Two paths that differ only in capitals** (`Main.js` and `main.js`, or folders `Data/` and
  `data/`) are an error: Windows sees them as one.
- **Real files only.** Symbolic links and submodules are errors. Do not use Git LFS: the
  collector would publish the pointer files.

## 4. File types and sizes

The extension is the part after the last dot. It must be one of these, in **lower case**
(`logo.PNG` is an error: rename it `logo.png`). A file with no extension is an error.

| Kind | Extensions |
|---|---|
| Pages and code | `html htm js mjs css map wasm` |
| Data | `json csv tsv txt md xml sqlite db pdf` |
| Images | `svg png jpg jpeg gif webp avif ico` |
| Fonts | `woff woff2 ttf otf` |
| 3D models | `stl glb gltf bin obj mtl` |

| Limit | Value |
|---|---|
| `gallery.toml` | 64 KB |
| One file | 25 MB (25 × 1024 × 1024 bytes) |
| One app, all files | 50 MB |
| All apps of the gallery together | 500 MB |

Keep files small anyway: people open apps on phones over mobile data.

## 5. Rules at run time (not checked by the collector)

- **Relative URLs only.** The app is served at `/<key>/<slug>/` (the trailing slash matters).
  Link `main.js`, `data/rates.csv`, `models/arch.glb`. A URL that starts with `/` points outside
  your app.
- **The platform's own URLs all start with `/_gallery/`.** Repo keys never start with `_`, so an
  app never clashes with them. The platform keeps every URL of its own under that prefix.
- **Data files** are fetched with relative URLs and are as private as the app: the same login and
  the same `[access]` roles protect them.
- **Third-party libraries** load from `cdn.jsdelivr.net`, `cdnjs.cloudflare.com` or `unpkg.com`
  with an exact version (`vue@3.4.38`, never `vue@3` or `vue@latest`), or are copied into the app
  folder.
- **What a `fetch` can get back** besides the file. Each answer is one line of plain text, which
  the app can show as it is:
  - **401** when the login has ended: "Your login has ended. Reload the page to log in again."
    A page load (opening or reloading the app) goes to the login instead and comes back.
  - **404** for a file that does not exist, a name the contract does not allow, or an app the
    user cannot open. The gallery answers an app the user may not open exactly as one that does
    not exist, so its name stays hidden.
- **All apps share one origin.** Prefix every `localStorage`, `sessionStorage` and IndexedDB key
  with the app id (`kiln/bricks:settings`), so apps never read each other's keys. Do not register
  service workers.
- **SQLite in the browser** (sql.js) downloads the whole file. Keep such files to a few MB; prefer
  JSON or CSV.
- Do not set `export-ignore` or other git attributes on the `gallery/` folder. The collector reads
  the committed blobs directly, so they change nothing, but they confuse the next reader.

## 6. The registry `repos.toml` (in the gallery repo)

The gallery's `repos.toml` names the repos it publishes:

```toml
[[repo]]
key    = "kiln"               # the URL prefix: /kiln/<slug>/
path   = "../VelKilnMaster"   # the local clone, relative to repos.toml's folder
branch = "main"               # default "main"
folder = "gallery"            # default "gallery"
```

- `key`: 1–40 characters, lower-case letters, digits and `-`, starting with a letter; unique.
- `branch`: no spaces, not starting with `-`.
- `folder`: one folder name, by the rules of § 3.
- Any other key is an error.

To add your repo, ask KLA to add an entry.

## 7. Versions

This is contract **1**. A platform change that breaks this contract raises the version; each
manifest names the version it was written for in `contract`, and the gallery refuses a version
it does not know.
