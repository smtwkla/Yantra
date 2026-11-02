# Yantra Help

Help is the app documentation for the plant's users: what is where in Yantra and how to do the daily
work, on real screens. It is kept apart from `docs/`, which is developer documentation (S103).

**Who reads it:** operators, technicians, engineers, managers and IT admin. The pages show the plant's
screens and the Masters set-up, so the gallery lets only Yantra's users open them.

**How it reaches the user:** the pages are plain web pages, published by SMTW's gallery
(<https://gallery.mspv.app>). The app only links to the Help home: the **Help** button in the top bar opens
<https://gallery.mspv.app/yantra/home/> in a new tab (`frontend/src/help.js`).

## What is here

This folder is Yantra's gallery folder: each subfolder is one gallery app with its `gallery.toml`; a file
directly in `help/` (this one, the outline) is not published.

| Path | What it is | Published at |
|---|---|---|
| `home/` | The Help home: one card per guide | `/yantra/home/` |
| `guide/` | The user guide: 72 slides, shown as a slide show (a screen 900 px wide or more) or as a page (a phone). `index.html` holds the text, the styles and a small script; `shots/` holds the 67 pictures (lossless WebP) | `/yantra/guide/` |
| `documents/` | Documents and photos: a reading page with its own pictures in `shots/` | `/yantra/documents/` |
| `guide-outline.md` | The screenshot list: who, where and the how-to lines of each shot, and the table slide id → shot → alt text | not published |

Each page stands alone: relative addresses only, no library, no service worker, no browser storage
(the gallery's app contract, `docs/SMTW-Utils-Gallery.md` in the Gallery repo). `tooling/tests/test_help_pages.py`
checks the pictures, the links, the ids and the manifests.

## See a page

Open each page's `index.html` itself in a browser (`help/guide/index.html`, `help/home/index.html`,
`help/documents/index.html`); from disk the home's `../guide/` link opens a folder listing, not the page.
On the guide, `?view=slides` or `?view=page` in the address chooses the view; `#x20` opens a slide.

## Publish a change

1. Commit the change. The gallery publishes only committed files.
2. KLA runs the Gallery repo's `tooling\run-collector.bat` (first with `--dry-run`). Nothing in the app or
   in the release does it.

The first time, the Gallery repo's `repos.toml` needs the entry `key = "yantra"`, `path = "../Yantra"`,
`folder = "help"`.

## Retake the screenshots

A tour action that fails (a renamed button, say) makes the run fail and names it (`tour action failed: …`);
fix the tour before you copy any shot.

A step that changes a screen does not touch the guide. Before a release that changes screens, on KLA's
word:

1. Start the dev DB (`tooling\dev\dev-db-up.bat`). Run `tooling\help-shots.bat`. It takes the e2e lock, starts
   a test stack on lane 9 with standard plant data, runs the tour (`frontend/help-tour/`) and stops
   everything. It writes only under `scratch/help-shots/`: `shots/` (PNG), `webp/` (lossless copies),
   `data.json`, the logs.
2. Look at the shots. Copy the `webp/*.webp` files that do not start with `doc-` into `help/guide/shots/` (and the `doc-*` files into
   `help/documents/shots/`). The table in `guide-outline.md` says which slide uses which file; a file name
   stays the same, so no page changes.
3. Change the version on the Help home, the guide's cover and its last slide (v0.1.15 + PM, screens of 02-11-2026) and the
   text of any slide whose screen changed.
4. Run `tooling\run-tooling-tests.bat`, then commit and publish as above.
