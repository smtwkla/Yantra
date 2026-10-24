Step: S034 — Defer, hold and follow-up date
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 24-10-2026

Reviewed against: 7a5b726 (the code is as at cbe8f02; uncommitted in the working tree: only the brief's `Status` line and the README index row)

**Verdict: no blocker or major finding.** Light track, so this is the only round. The brief meets every light criterion (no migration, no RBAC, no locking, no new endpoint, no new dependency, about 10 files). Five minor findings, mostly places where the old words or the old line shape survive outside the files the brief lists; five nits.

Facts file read: `scratch/brief-facts-S034.md`. Every file and code name it lists exists where the brief says; the four "not found" names are new by design.

## Minor

### BR1-01 — minor — `MoveDialog.vue` still says "Choose the planned date"

**Problem.** § 3 says `MoveDialog.vue` needs no change. Its own pre-check does: `missingField()` at line 139 returns `["planned_date", "Choose the planned date"]` before any request reaches the server. With § 1d the server says "Choose a date", but the user never sees the server's text when the field is empty: the dialog's own message shows first. A user who leaves *Check again by* empty reads "Choose the planned date" under a field that is not called that.

**Why it matters.** It is the exact mismatch § 1d removes, left in the one place the user actually meets it.

**Options.**
- (a) **Recommended.** Add `MoveDialog.vue` to § 3: line 139 reads "Choose a date" (the same text as `PLANNED_DATE_NEEDED`), and the header comment's "S019 schedule / change plan … Schedule opens with the date empty" gets the new words. The `ScheduleFields.vue` header comment (line 3, "*Schedule* and *Change plan*") changes too.
- (b) Leave it and let the e2e test catch it. It would not: no test sends an empty date through the screen.

### BR1-02 — minor — the list row's text on an overdue "check" ticket, and two S019 e2e assertions the brief does not name

**Problem.** § 1b's table puts "Plan line (ticket header, list row)" in one row and "Plan line past the date: *Check due since*" in the next. The code has two helpers: `planLine(ticket)` (the header; knows `overdue`) and `planText(plannedDate, reason)` (the list row, `TicketsView.vue` line 199; knows nothing of overdue). The list row of an overdue parts wait will therefore read "Overdue · check by 23-10-2026 · waiting for parts", with the red badge "Overdue since 23-10" above it. The brief does not say whether that is intended, and the coder has to decide it alone.

Two S019 e2e tests assert the old "for …" shape with a *check* reason, and are not caught by § 5's "tests that look up *Schedule* / *Scheduled*":
- `tickets-work.spec.js` line 426 (Overdue filter): `Overdue · for ${date} · waiting for parts`;
- line 401 (breakdown for parts): `.plan-line` `for ${date} · waiting for parts`.

**Why it matters.** The coder changes a shared helper and finds two red tests the brief said would stay green, or writes the list row one way and the header another.

**Options.**
- (a) **Recommended.** State in § 1b that the list row keeps `planText()` ("check by …" also past the date; the red badge beside it already says *Overdue since*), and list the two assertions in § 3 / § 5 as changing by design.
- (b) Give the list row `planLine()`'s overdue shape too (pass `overdue` into `planText`). More change for a row that already carries the red badge.

### BR1-03 — minor — `device-checks.md` row 10 tells IT Admin to press *Schedule* and tap *Planned date*

**Problem.** Row 10 (S019, open) reads: "press **Schedule**, and tap **Planned date** … choose *Waiting for parts*, and press **Schedule**. Under the ticket's number the page now shows 'for DD-MM-YYYY · waiting for parts'". After S034 the button reads *Defer*, the field *Check again by*, and the line "check by DD-MM-YYYY · waiting for parts". § 5 says "The date input itself is S019's open row 10" but § 3 does not list the file.

**Why it matters.** The person doing the check looks for a button that does not exist and reports a failure.

**Options.**
- (a) **Recommended.** Add `docs/steps/device-checks.md` row 10 to § 3: the coder rewrites the row's steps and expected text in S034's words (the check itself is unchanged: the phone's date picker and DD-MM-YYYY).
- (b) Leave the row and let the planner fix it at gate B. It is the same edit, later.

### BR1-04 — minor — three words for the breakdown's held state: *Put on hold*, *Waiting*, *On hold*

**Problem.** On a breakdown the user presses **Put on hold**, the badge then reads **Waiting**, the list filter that finds it reads **On hold**, and the timeline line reads **On hold**. On a defect the chain is consistent (*Defer* → *Deferred*), on a breakdown it is not. Scope B asks for the same word for the same thing across the app. § 6 Q1 asks the user about the words, but offers only *Hold* for *Put on hold*; it does not raise this chain.

**Why it matters.** A supervisor told "the press is on hold" opens the list, sees *Waiting* on the row, and is not sure it is the same thing. A judgement call for the user, so not a nit.

**Options.**
- (a) As written: *Waiting* was the user's S019 decision (U1 Q2), and it tells the floor the machine is down and idle.
- (b) **Recommended.** Keep the two badges the user chose (*Deferred*, *Waiting*) and name the filter after them: **Deferred / Waiting** instead of *On hold*. The filter then lists exactly the words a user scans for on the rows. *On hold* stays on the button (*Put on hold*) and on the neutral timeline line. `STATE_LABELS.scheduled` can read *On hold* as a fallback.
- (c) Badge *On hold* for the breakdown too, so the button and badge match (*Put on hold* → *On hold*), and the filter *On hold* covers it; the defect's *Deferred* is then the only badge the filter's name does not say. This reverses S019 U1 Q2.

Add the chosen option to § 6 Q1 for the user.

### BR1-05 — minor — "Check due since 25-10-2026" is hard to read; one phrase would do

**Problem.** § 1b introduces a second overdue phrase for the header line: "**Check due since** 25-10-2026 · waiting for parts". "Check due since" is not a phrase an English reader parses at once ("the check is due since …"), and a Tamil-speaking engineer will not do better. Decision 4 keeps the badge at one word, *Overdue*, for the same reason: one word, one filter. The line already says what kind of wait it is ("waiting for parts").

**Why it matters.** The brief specifies UI text (scope B), and this one is the line a user reads first on an overdue ticket.

**Options.**
- (a) **Recommended.** One phrase for both kinds: "Overdue since 25-10-2026 · waiting for parts". `planLine()` then changes nothing past the date; only the not-yet-due line differs by kind ("for …" / "check by …"). Fewer words, fewer tests.
- (b) Keep two phrases but plainer: "Check was due 25-10-2026 · waiting for parts".

A judgement call on wording the user reads, so minor rather than nit.

## Nits

- **BR1-06** (nit) § 2 SMRP: say it in SMRP's own two terms. SMRP measures backlog as *planned backlog* (work with a job plan) and *ready backlog* (planned **and** materials on hand). Work waiting for parts is in the planned backlog but **not** in the ready backlog; the "check again by" date is the review of that not-ready work. "SMRP backlog management" is not a named SMRP metric; cite by name only, as S019 § 9 Q7 settled (the user has no SMRP copy). The EN 13306 bullet is right: *deferred corrective maintenance* is corrective maintenance not carried out at once after fault detection but delayed according to given maintenance rules; *logistic delay* is time maintenance cannot proceed because resources (parts, people, tools) must be acquired; *administrative delay* is time lost to administrative reasons (a decision, a permit). One more line would help the owner: a defect waiting for parts is **both** deferred corrective maintenance (the plant chose to run on) and logistic delay (the wait itself); the brief's rule picks the button word by the first and the date word by the second, which is consistent.
- **BR1-07** (nit) § 3 `test_ticket_work_api.py`: the literal messages are at lines 1020, 1023, **1025** ("Plan within a year") and 1079; 1025 is missing from the list.
- **BR1-08** (nit) § 1c quick-pick labels: "+7 days" does not start with a verb or read as a result (scope B). "In 7 days", "In 14 days", "In 30 days" read as what the date will be; or keep "+7 days" and say in the brief that it is a deliberate chip form.
- **BR1-09** (nit) § 1b help text: "chase" is colloquial; "When should someone follow this up? If the supplier gave a date, use it." Also § 5's "+14 days" e2e check: the component adds 14 days to the **phone's local date**, the e2e helper `istDay()` uses IST; compute the expected value the same way the component does (or from the date input's `min`), or the test is wrong on a laptop whose clock is not IST.
- **BR1-10** (nit) § 1a "*Change plan* … stay as they are" is about its words; say also that its dialog uses the same `ScheduleFields.vue`, so the reason-first order, the label by reason, the help and the quick picks appear there too (with the reason prefilled, the label is right at once). Otherwise a coder may read "stay as they are" as "do not touch".

## Checked and found consistent

- Light criteria: all met; `Track: light` is right.
- `moveLabel()` / `moveSaveLabel()` already take `intensity`; `MoveDialog.vue` lines 184 and 188 and `TicketDetailView.vue` lines 230, 248, 266, 271 pass `ticket.intensity`, so the button and Save words change in `ticketLabels.js` alone, as § 3 says.
- `stateLabel()` is the only place the badge word is made; `TicketsView.vue` and `TicketDetailView.vue` both call it. No other screen (equipment page, S029 ticket light, alerts, push text) shows *Schedule* / *Scheduled* to a user: `alerts_core.py` uses `scheduled` only as a state name in a comment; `TICKET_LIGHT_LABELS` has no state word; `screens.spec.js` and the other specs do not look the words up.
- Backend `EVENT_LABELS[SCHEDULED_EVENT]` is used only in `validate_event_time`'s "Must be at or after <label>, <time>"; "On hold" reads fine there. No backend test asserts the "Scheduled" label text.
- `formatDateTime("2026-10-25")` → "25-10-2026", so "check by 25-10-2026" needs no new formatter.
- The three backend message constants are used only in `tickets_core.py` and imported by `test_tickets_core.py`; the literals live only in `test_ticket_work_api.py` (BR1-07 for the one missed line).
- `frontend/tests/ticketLabels.test.js` lines 24, 181, 189–198, 235 are the assertions § 5 changes; the brief names them by subject.
- `openAction()` runs `expectDialogFits` on every dialog it opens, so the Defer / Put on hold dialog with the help line and three quick-pick buttons is checked for phone fit by the existing S019 tests on Pixel 7 and iPhone 14; no new device check is needed, as § 5 says.
- `planDateKind` as a frontend label rule: consistent with S019 BR1-06 (reason labels live in `ticketLabels.js`, the server checks only the codes). It is a third classification beside `WAITING_REASON_DELAYS` (approval is administrative but *check*), stated as such in § 1b; the test that lists all six codes guards a new reason.
- Decision 3 (date stays required) follows S019 decision 2 and the user's request 3; the quick picks answer request 2 without a bypass.
- Plan.MD § 4.2 line 377 ("shown as *Scheduled* on a defect") and Maintenance-Philosophy § 7 lines 180–190 are the doc lines to change; both named in § 3.
- Writing style (scope A): the brief leads with the request, one idea per sentence, one term per thing except the chain BR1-04 raises.
