Step: S036 — Ticket tint by intensity
Doc: brief
Author: Planner (Opus)
Date: 24-10-2026
Track: light
Status: Done (committed 15b06e0; checks: 1 auto; row 31, not important, open)
Baseline: e451c33 + uncommitted S035

# S036 — Ticket tint by intensity

**The request (KLA, 24-10-2026).** "Mild bg colour on ticket, based on status —
mild pink, yellow, grey." The user's answer (U1, 24-10-2026): by **intensity**,
the same three colours as today's intensity badges.

**Track: light.** No migration, no data change, no RBAC, no endpoint, no new
dependency. Frontend only, about 7 files, on the existing Bootstrap classes.

## 1. What will be built

1. **A mild background by intensity** on every open ticket:

   | Intensity | Badge today (`INTENSITY_BADGE_CLASS`, `ticketLabels.js:18`) | Tint |
   |---|---|---|
   | `critical` — *Breakdown* | `text-bg-danger` | mild pink (`#f8d7da`, Bootstrap `danger` subtle) |
   | `degraded` — *Defect* | `text-bg-warning` | mild yellow (`#fff3cd`, `warning` subtle) |
   | `initial` — *Defect · initial* | `text-bg-secondary` | mild grey (`#e2e3e5`, `secondary` subtle) |

   A **closed** ticket (`state === "closed"`) has no tint. Every other state
   (raised, acknowledged, scheduled, in progress, back in service) is tinted:
   *back in service* is not closed yet, and still needs someone (S018).
2. **Where:**
   - **ticket rows** in `TicketRow.vue`, the one row component of the Tickets
     list (`TicketsView.vue:177`) and the Me page's two ticket tabs
     (`MeView.vue:182`);
   - the **Open tickets** rows on the equipment page
     (`EquipmentDetailView.vue:202–214`), which draw their own row;
   - the **ticket page**: the title row only — serial, intensity badge, state
     badge, *Not a fault* (`TicketDetailView.vue:212–217`), as a rounded panel.
     The plan line, the action bar and the cards below stay on the plain page.
3. **The badge stays.** The badge text says the intensity, so colour is never
   the only sign (WCAG 2.1 SC 1.4.1).
4. **Grey text stays readable on a tint.** Inside a tinted row or panel, the
   small grey text (`.text-secondary`, `#6c757d`) is drawn darker (Bootstrap's
   `--bs-secondary-text-emphasis`, `#2b2f32`, its token for text on a subtle
   background; BR1-03). See § 2 for the figures.

### Out of scope

- Tint by state, or a colour for *Overdue* (the red *Overdue since* badge stays
  as it is).
- Dark mode: the app has none (no `data-bs-theme` and no
  `prefers-color-scheme` in `frontend/src` or `index.html`, checked
  24-10-2026). The tokens used follow Bootstrap's own dark values if one comes.
- The raise screen's three intensity buttons, `MoveDialog` and
  `RegradeDialog`: they show an intensity choice, not a ticket.
- Print views.

## 2. Standards and practice

- **WCAG 2.1 SC 1.4.1 (use of colour):** colour is not the only way to show
  information. The intensity badge keeps its words.
- **WCAG 2.1 SC 1.4.3 (contrast, minimum):** normal text needs 4.5:1. Measured
  on 24-10-2026 with the WCAG formula (`node -e`); the hover colours are
  Bootstrap 5.3.8's `--bs-*-border-subtle` (light theme), which the list-group
  variants use as their hover background:

  | Text | on white | pink `#f8d7da` | yellow `#fff3cd` | grey `#e2e3e5` | pink hover `#f1aeb5` | yellow hover `#ffe69c` | grey hover `#c4c8cb` |
  |---|---|---|---|---|---|---|---|
  | body `#212529` | 15.43 | 11.55 | 13.92 | 12.01 | 8.42 | 12.53 | 9.16 |
  | grey `#6c757d` | 4.69 | **3.51** | **4.23** | **3.65** | **2.56** | **3.81** | **2.78** |
  | darker grey `#2b2f32` (`--bs-secondary-text-emphasis`, BR1-03; figures corrected after S036 CR1) | — | 10.11 | 12.19 | 10.51 | 7.37 | 10.96 | 8.02 |

  The row's body text is not `#212529` on a clickable row: `.list-group-item-action`
  (`bootstrap.css:5063`) keeps `--bs-list-group-action-color`,
  `rgba(33,37,41,.75)`, and the variant leaves it as it is (BR1-01). Blended,
  it gives 5.73 on pink, 6.37 on yellow, 5.86 on grey; on hover 4.79, 6.06,
  4.98. All pass, so the row text keeps today's colour.

  So only the small grey text must be darker on a tint (§ 1.4). Lighter tints do not
  solve it: even a 40 % pink (`#fceff0`) gives only 4.19.
- **Visual management (TPM, the red tag).** A breakdown that stands out in a
  list is the same idea as the red tag on the machine: the abnormal is seen
  at a glance.

## 3. Where

- `frontend/src/utils/ticketLabels.js`: `INTENSITY_TINT` (intensity → the
  Bootstrap colour name: `danger`, `warning`, `secondary`) and
  `ticketTint(ticket)` → that name, or `null` for a closed ticket or an
  unknown intensity.
- `frontend/src/components/TicketRow.vue`: the row gets
  `list-group-item-<name>` and `ticket-tinted` when `ticketTint` is not null.
- `frontend/src/views/EquipmentDetailView.vue`: the same on its Open tickets
  rows (they are open by the query, `state=open`, line 72).
- `frontend/src/views/TicketDetailView.vue`: the title row (lines 212–217)
  gets `bg-<name>-subtle border border-<name>-subtle rounded px-2 py-1` when
  `ticketTint` is not null. No `ticket-tinted`: the title row holds no
  `.text-secondary` (BR1-04).
- `frontend/src/assets/main.css`: one rule,
  `.ticket-tinted .text-secondary { color: var(--bs-secondary-text-emphasis) !important; }`.
  `!important` is needed because Bootstrap's `.text-secondary` has it.
- `frontend/tests/ticketLabels.test.js`: `ticketTint` cases.
- `frontend/e2e/tickets-work.spec.js`: the e2e test (§ 5).

## 4. Design decisions

1. **Bootstrap's list-group variants for rows** (`list-group-item-danger`,
   `-warning`, `-secondary`, Bootstrap 5.3.8). They set the row's background,
   its border and its own hover and active colours
   (`--bs-list-group-action-hover-bg`), so the row still shows it is a link.
   Rejected: `bg-danger-subtle` on the row. It has `!important`, so it would
   hide the hover colour of `list-group-item-action`.
2. **Background only; the row text keeps today's colour** (BR1-01). On a
   clickable row the variant changes the background, border and hover, not
   the text colour (`.list-group-item-action` sets it after the variant). The
   text passes on every tint (§ 2). Rejected: a CSS line for the variant's
   dark emphasis text (`--bs-danger-text-emphasis`); the user asked for a
   background.
3. **Ticket page: the title row only.** Rejected: the whole page background.
   The cards, buttons and the red plan line of an overdue ticket would sit on
   pink, and red text on pink is 3.39:1.
4. **One helper for the colour name** in `ticketLabels.js`, used by the three
   screens. Rejected: the class strings in each screen.
5. **Closed tickets plain.** U1. A closed list shows past work, and a tint
   there would make old breakdowns look current.
6. **The tint is the intensity, the bulb is the machine** (BR1-05). The S029
   status bulb says whether the machine is down now; the tint says how the
   ticket was graded. A breakdown back in service shows an amber bulb and a
   pink row: the machine runs, the breakdown ticket is still open.

## 5. Tests and acceptance

### Unit (vitest, `frontend/tests/ticketLabels.test.js`)

- `ticketTint` for `critical`, `degraded`, `initial` in an open state gives
  `danger`, `warning`, `secondary`.
- `back_in_service` is tinted; `closed` gives `null` for each intensity.
- An unknown intensity gives `null`.

### Automated (e2e, `frontend/e2e/tickets-work.spec.js`, targeted)

- **Important.** One test, set up by API per the S024 conventions: one open
  breakdown, one open defect, and one closed ticket. On the Tickets list with
  the filter *All*, the breakdown row's background is pink
  (`toHaveCSS("background-color", "rgb(248, 215, 218)")`), the defect row's
  yellow (`rgb(255, 243, 205)`), and the closed row's white (BR1-02: what the
  user sees; the class names may be asserted too). The breakdown's ticket page
  shows its title panel pink.
- The coder runs `tickets-work.spec.js`, `me.spec.js`, `equipment.spec.js`
  and `screens.spec.js` (targeted: no shared frontend code changes).

### On a real device

Not important (BR1-06): on a phone on the shop floor, the three tints can be
 told apart in daylight and under the hall lights (any login with Tickets,
 production or the dev server). Contrast is measured in § 2.

## 6. Open questions and assumptions

1. **The tint names** (assumption): Bootstrap's own subtle colours, as in
   § 1.1. If the user wants them lighter, only the CSS changes.
2. **A yellow badge on a yellow row** (assumption): the *Defect* badge
   (`#ffc107`) sits on `#fff3cd` at 1.47:1 as a shape. Its text is black on
   amber (12.88:1), so the word stays readable. Accepted as it is.

## 7. Amendments

None.

## 8. Review log

### U1 — user answer, 24-10-2026 (before drafting)

- The tint follows the intensity: Critical pink, Degraded yellow, Initial
  grey. Closed tickets have none.

### Round 1 — `2-brief-review-r1.md` (Fable), answered 24-10-2026

0 blocker, 0 major, 2 minor, 5 nits. Light track: the only round.

| Finding | Answer |
|---|---|
| BR1-01 minor — the variant does not change a clickable row's text colour | Accepted (a): § 2 figures added, decision 2 rewritten to a background-only tint |
| BR1-02 minor — the e2e test asserted classes | Accepted: `toHaveCSS` background colours on the rows and the title panel |
| BR1-03…BR1-07 nits | Accepted. BR1-03: `--bs-secondary-text-emphasis`. BR1-04: no `ticket-tinted` on the title row. BR1-05: decision 6 (tint vs bulb). BR1-06: one plain device check. BR1-07: index row set to Gate A. |

### U2 — approval, 24-10-2026

- Approved by KLA after review round 1, with § 6 assumptions 1 and 2 as written.
