Step: S036 — Ticket tint by intensity
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 24-10-2026

Reviewed against: e451c33 + uncommitted S035

# S036 — Brief review, round 1

**Verdict: no `blocker` or `major` finding. Two `minor` findings and five nits.** The
brief meets every light-track criterion (no migration, no RBAC, no transaction, no new
endpoint or dependency, 7 files on an existing Bootstrap pattern); this is the only review
round. The brief can go to the user once the two minors are answered.

Facts file: `scratch/brief-facts-S036.md`. Every file, test and code name it lists exists
where the brief says; `INTENSITY_TINT` and `ticketTint` are new, as the brief says. I opened
Bootstrap 5.3.8's compiled CSS (`frontend/node_modules/bootstrap/dist/css/bootstrap.css`)
for the behaviour claims in § 4, and recomputed every contrast figure in § 2 and § 6 with the
WCAG formula; they all match.

## Findings

### BR1-01 — minor — § 4.2: the list-group variant does not change the row's text colour

**Problem.** § 4.2 says the variant "also sets the row's text colour to the variant's dark
emphasis (`--bs-danger-text-emphasis`, `#58151c`)". On the ticket rows it does not. Every
row is a `list-group-item-action` (a `router-link`, `TicketRow.vue:16`,
`EquipmentDetailView.vue:205`), and in Bootstrap 5.3.8:

- `.list-group-item` (bootstrap.css:5027) sets `color: var(--bs-list-group-color)`;
- `.list-group-item-action` (bootstrap.css:5063, later in the file, same specificity)
  sets `color: var(--bs-list-group-action-color)` and wins;
- `.list-group-item-danger` (bootstrap.css:5297) overrides `--bs-list-group-color` and
  the hover and active colours, but not `--bs-list-group-action-color`, which stays
  `var(--bs-secondary-color)` = `rgba(33, 37, 41, 0.75)`.

So the serial, machine and problem text keep today's colour (body at 75 %). Blended on each
tint that is `#575255` on pink (5.73:1), `#595952` on yellow (6.37:1), `#515558` on grey
(5.86:1); on the hover colours 4.79, 6.06 and 4.98. All pass 4.5:1. On hover the text goes
black (`--bs-emphasis-color`), as the variant sets.

**Why it matters.** The decision's accepted outcome ("the text stays dark and readable" in
dark red) is not what the screen will show, and its rejected alternative is moot. The coder
or the user would look for a colour that is not there. The § 2 table's "body `#212529`" row
is the ticket page's text, not the rows'. The result itself is good: it is the background
tint the user asked for, with the text unchanged.

**Options.**
- (a) **Recommended.** Rewrite § 4.2 to the real behaviour: the row's text keeps Bootstrap's
  action colour (`--bs-list-group-action-color`, body at 75 %); only the background, the
  border and the hover and active colours change. Add the blended figures above to the § 2
  table, or a line under it. The ticket page's title row keeps `#212529` (11.55:1 on pink),
  so rows and page agree: a tint, no new text colour.
- (b) If the dark emphasis text is wanted after all, one line does it:
  `.ticket-tinted { --bs-list-group-action-color: var(--bs-list-group-color); }`. That goes
  beyond the request ("mild bg colour") and gives three text colours in one list; the user
  would have to choose it.

### BR1-02 — minor — § 5: the e2e test asserts class names, not what the user sees

**Problem.** The automated check asserts `list-group-item-danger`, `list-group-item-warning`
and `bg-danger-subtle` on the elements. `docs/steps/README.md` § Manual checks: a test
"asserts what the user would see". The user sees a pink background, not a class.

**Why it matters.** A class assertion passes even when the class has no effect (a CSS import
order change, a future Bootstrap upgrade that renames the variant's variables). The cost of
the stronger check is one line per element.

**Options.**
- (a) **Recommended.** Assert the computed colour: the breakdown row
  `toHaveCSS("background-color", "rgb(248, 215, 218)")`, the defect row
  `rgb(255, 243, 205)`, the closed row `rgb(255, 255, 255)` (Bootstrap's `--bs-body-bg`),
  and the title panel `rgb(248, 215, 218)`. Keep the class checks too if the coder wants
  the clearer failure message.
- (b) Keep the class checks only, and say so in § 5.

## Nits

- **BR1-03** (nit) § 3 `main.css`: use `var(--bs-secondary-text-emphasis)` (`#2b2f32`:
  10.11:1 on pink, 12.19 on yellow, 10.51 on grey, 7.37 on pink hover) instead of
  `var(--bs-gray-800)`. It is Bootstrap's own token for text on a subtle background, and it
  flips with `data-bs-theme`, which makes the § 1 Out-of-scope sentence ("the tokens used
  follow Bootstrap's own dark values if one comes") true; `--bs-gray-800` is a fixed
  palette value and does not flip.
- **BR1-04** (nit) § 1.2 and § 3 `TicketDetailView.vue`: the title row (lines 212–217) has
  no `.text-secondary` inside it (an `h4` and three badges), so `ticket-tinted` does nothing
  there. Drop it from the title row, or say why it is kept.
- **BR1-05** (nit) § 1.1: add one sentence on how the tint relates to the S029 bulb, so the
  coder and the user do not read a contradiction: a breakdown that is back in service shows
  an **amber** bulb on the equipment list (the machine runs) but a **pink** row here (its
  intensity, until it is closed). Both are by design; the badge text says which.
- **BR1-06** (nit) § 5 On a real device: consider one plain (not important) row for IT
  Admin: "on a Galaxy phone on the floor, the three tints can be told apart" — production on
  the TEST machine, any account with tickets. A browser measures contrast; it cannot judge a
  mild tint in plant light. The brief's "None" is defensible; the user decides.
- **BR1-07** (nit) `docs/steps/README.md` index: the S036 row says `Draft`, the brief's
  header says `In review`. Update the row (README § Gates: whoever changes the status
  updates the row).

## Checked and found consistent

- **Facts.** All seven files exist; `INTENSITY_BADGE_CLASS` is at `ticketLabels.js:18`;
  `TicketRow` is the one row component of `TicketsView.vue:177` and `MeView.vue:182`; the
  equipment page draws its own rows at `EquipmentDetailView.vue:201–214` and loads them with
  `state=open` (line 72); the ticket page's title row is lines 212–217; `MoveDialog` and
  `RegradeDialog` are components used in `TicketDetailView.vue`.
- **Bootstrap 5.3.8** is what is installed (`node_modules/bootstrap/package.json`), imported
  once in `main.js` before `main.css`. The three list-group variants exist with the
  variables the brief names (`--bs-list-group-action-hover-bg` = the border-subtle colour).
  `.text-secondary` has `!important` (bootstrap.css:8500), so the brief's `!important` is
  needed, and `.ticket-tinted .text-secondary` beats it on specificity. `bg-danger-subtle`
  has `!important` (bootstrap.css:8908), so § 4.1's reason to reject it on rows is right.
- **Tokens.** `#f8d7da`, `#fff3cd`, `#e2e3e5` are the light `*-bg-subtle` values;
  `#f1aeb5`, `#ffe69c`, `#c4c8cb` the `*-border-subtle`; `#58151c` is
  `--bs-danger-text-emphasis`; `--bs-gray-800` is `#343a40`.
- **Contrast figures** in § 2 (all 21 cells), § 4.2 (10.22), § 4.3 (3.39) and § 6.2 (1.47,
  12.88) recomputed and correct. The 40 % pink figure (4.19) too.
- **Dark mode**: no `data-bs-theme` or `prefers-color-scheme` in `frontend/src` or
  `index.html`, as § 1 says.
- **The list items carry `state`** (`backend/tickets.py:206`), so `ticketTint(ticket)` can
  read it on every screen. `STATE_FILTERS` has `all` and the list reads it from the URL
  (`TicketsView.vue:45`), so the e2e test can open `/tickets?state=all`.
- **e2e conventions.** Setup by API exists: `raiseByApi`, `moveByApi` (a close with cause
  and action by API is used in `tickets-parts.spec.js:281`). The S019 Overdue test in
  `tickets-work.spec.js:420` is the model for a list-row assertion.
- **Unit tests** go into the existing `ticketLabels.test.js` describe blocks' style.
- **Standards.** WCAG 2.1 SC 1.4.1 and 1.4.3 cited correctly, with the 4.5:1 threshold for
  normal text. The TPM red-tag reading matches `docs/Maintenance-Philosophy.md` § 6 ("the
  red tag is the breakdown ticket").
- **Design and structure.** The one rule (intensity → colour name, closed → none) lives in
  the pure `ticketLabels.js` beside `INTENSITY_BADGE_CLASS`; the templates only add classes.
  No new abstraction, no backend change.
- **UX.** Nothing is added to tap or type; no new text (nothing for scope B); layout and tap
  targets unchanged. The badge keeps the words, so the tint is a second sign, not the only
  one. Closed tickets plain (U1) is right for the Me page's *tickets I raised* tab and the
  *All* / *Closed* filters.
- **Light track.** Every criterion holds; the targeted spec list in § 5 is right (`main.css`
  is not in the README's shared-code list).
