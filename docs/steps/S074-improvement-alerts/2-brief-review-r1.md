```
Step: S074 — Improvement alerts
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 30-10-2026
From: R05.5
```

Reviewed against: 32eb122 + uncommitted S066, S067, S068, S069, S070 (partly: v38 and the core are in the tree, the routes are not); S071–S073 approved, not coded (read from their briefs).

**Verdict: no `blocker` or `major` finding is open.** Four `minor` findings and seven nits. Three of the minors (BR1-01, BR1-02, BR1-03) are judgement calls for KLA; **none is defining**: each is an internal mechanism or a delivery setting inside gate R's Q5.1 (a), and no screen or approved decision changes with either answer. § 9's Q1–Q3 are not defining either. The step can be coded after the Review log answers these.

Facts file used: `scratch/brief-facts-S074.md`. Every file, test and code name it lists as existing was checked; the names it reports "not found" are new in this step or in S070/S072, as the brief says. `targetUrl` is listed "not found" only because `frontend/public` is outside the *Code folders* setting; it is at `frontend/public/sw.js:38`, as the brief cites.

## Findings

### BR1-01 — minor — the "once" rule `alerted_for < end` can lose an alert when the end moves earlier

**Problem.** § 5.1 defines `overdue_alert_due` with `alerted_for is None or alerted_for < due_date` and `ready_alert_due` with `alerted_for < watch_until`. § 8.1 pins it ("alerted for a later date (moved earlier) → False"). Two cases then alert never, although the record is overdue or ready again:

- The watch end moves earlier after the marker was written: the scan marks `ready_alert_for = 18-02 15:30` and queues the task; `watch_days` is cut to 60 before the task runs → the task sees a different end and does not send (§ 5.3's table, right); the next scan sees `18-02 < 19-01` false → no alert, ever, while the improvement shows *Ready to verify*.
- A watch restarted with a back-dated done (S072 D11: `done_at` may go back to the problem's time): the new `watch_from` is earlier, the new end can be earlier than the alerted one → the same.

The first window is seconds (the worker drains at once), the second is rare. For `overdue_alert_for` the same `<` means a due date moved earlier, still past, alerts no more; that one is defensible (the owner was told).

**Why it matters.** § 1 promises *Ready to verify* "once per watch end". With `<` it is "once per watch end, unless a later end is earlier", a rule nobody will remember, and the one case that loses the alert is the one where a verifier changed the watch.

**Options.**
- (a) `alerted_for != end` for both rules: literally once per due date and once per watch end. A due date moved earlier, still past, alerts again (the countermeasure is overdue against a new date); a watch whose end moved after an alert alerts again at the new end. Bounded by edits. § 8.1's "moved earlier → False" case flips to True.
- (b) Keep `<` and state the two lost cases in § 5.1 as accepted.

**Recommendation:** (a). Simpler to say and to test. KLA's call; not defining.

### BR1-02 — minor — D3 does not answer S072 D1, which left the "once" memory to a timeline line

**Problem.** D3 chooses two marker columns (v40) and rejects "a timeline line as the marker (the timeline records what people did, S072 § 5.6)". But S072 D1, approved, says: "R05.5 adds the daily task its alerts need ('watch ended' once per improvement) and **may store a line then**." S072 also already stores actor-less lines (`state_changed` from the settle; the backfill's lines). So the rejected option was the approved step's own suggestion, and the brief's reason for rejecting it does not hold as written.

**Why it matters.** The migration is the brief's one departure from the roadmap ("Migrations: none"). KLA should see that the no-migration road was the one S072 pointed at, and why the column still wins, before approving the departure.

**Options.**
- (a) Keep the columns and complete D3: a stored `watch_ended` line would double S072's computed `watch_ended` line (§ 5.6 there) unless S072's computed line is removed; "once per due date" needs a value to compare (the due date alerted for), which a line holds only in its text; and the scan's candidate query would join `improvement_events` per countermeasure. One nullable column per table is the smaller change.
- (b) Store `watch_ended` as an `improvement_events` line (`event = 'watch_ended'`, `occurred_at = watch_until`) as the ready marker, drop S072's computed line, and keep only `overdue_alert_for` as a column (still a migration, one column).
- (c) Both markers as lines (`overdue_alerted` with `action_id` and the due date in `remark`): no migration, as the roadmap said; the scan reads the latest such line per countermeasure.

**Recommendation:** (a), with D3 rewritten to cite S072 D1 and the three reasons. KLA's call; not defining.

### BR1-03 — minor — D7's "quiet" also means Urgency `low`, which may hold the alert until the phone charges or joins Wi-Fi

**Problem.** `push_core.send_task_payload` (`backend/push_core.py:176`) derives both fields from `quiet`: `urgency = "low"`, `silent = True`. D7 wants quiet for "no breakdown sound" and names the urgency consequence as "may hold a message until the phone charges or joins Wi-Fi". RFC 8030 § 5.3's table says `low` = delivered when the device is on power **or** on Wi-Fi. A technician on battery and mobile data may get *Countermeasure for you* only in the evening. The defect alert already lives with this; for a job handed to a person it is a stronger trade-off, and it also decides the device check: § 8.5 row 1 ("the phone shows … quietly") can appear to fail on a phone that is on battery and mobile data.

**Options.**
- (a) Keep `quiet` as it is (silent and low), and say so in D7 and in § 8.5 row 1 ("phone charging or on Wi-Fi; Urgency low may otherwise delay it"). The 24-hour TTL is the mitigation, as D7 says.
- (b) Silent without low urgency: `improvement_message` carries `urgency: "normal"` and `send_task_payload` reads it when present (two lines in `push_core`, one test); tickets unchanged. No sound, but delivered as a normal push.

**Recommendation:** (a) for this step (one rule for every quiet alert; the row's note makes the device check honest). KLA's call; not defining.

### BR1-04 — minor — the "Through the worker" test would post to the real push service unless the sender is faked

**Problem.** § 8.2 runs `Worker.run_once` with `SCHEDULE` patched to the scan. `run_once` then drains every due task in the loop (`backend/worker.py:184`): the scan, then the `improvement_alert` tasks it queued, then their `push_send` tasks, and `push_send` calls `push_sender.send` (pywebpush → an HTTPS POST to the `fcm.googleapis.com` test endpoint of `add_device`, `PUSH_TIMEOUT_SECONDS` 10). Push is on in the test session (`conftest.py:76-90`), so the call is real. The existing worker tests patch the sender (`test_alerts.py:559`, `fake_send`).

**Why it matters.** A unit test that reaches the network is slow and flaky, and would mark the plant's devices' `last_error`.

**Options.**
- (a) `monkeypatch.setattr(push_sender, "send", fake_send(201))` in that test, and assert the scan `done`, each `improvement_alert` `done`, and the `push_send` rows `done` with the fake's calls.
- (b) Run that test with `push_off`: the scan writes the markers and queues the alert tasks; each alert task logs "push is not set up" and is done; assert the markers and the task rows (this also proves D8 through the worker).

**Recommendation:** (a) for the happy path and (b) as the D8 case. The coder's to do; no decision needed.

## Nits

- **BR1-05** (nit) § 8.3: "S070 § 8.2 asserts no task rows" — S070's brief asserts nothing about `task_queue` (its § 5.9 says "no background task, no alert"). Also, S070 is being coded, so `test_improvement_actions_api.py` may land under another name. Write: "the coder checks S070's countermeasure tests, wherever they are, for a `task_queue` assertion".
- **BR1-06** (nit) § 3 or § 7: state the import direction, as S067 does: `alerts_core` imports `improvements_core` (pure → pure: `IMPROVEMENT_OPEN_STATES`, `ACTION_OPEN`, `watch_until`); `alerts.py` imports `access_core.roles_holding` and `improvements_core`, never `improvements.py`; `improvements.py` imports `alerts` (as `tickets.py:101` does). No cycle: `alerts.py` imports `settings`, `task_queue`, `tickets_core` only.
- **BR1-07** (nit) § 5.2 step 2 calls the candidate reads "the transaction's first reads" while step 1's `SELECT NOW()` comes first. It is right (a `SELECT` with no table opens no InnoDB snapshot), but say so in one clause, or the coder will reorder the steps.
- **BR1-08** (nit) § 5.6: `people_at_unit(cur, site, units, …)` reads memberships at the improvement's site only. A machine moved to a unit of another site is visible to that site's readers through `m.unit_id` (`unit_access_condition`), who get no alert. Rare (the improvement's site is fixed, S067); say it is accepted.
- **BR1-09** (nit) § 8.5: give each row the device-check table's *Network* value (company Wi-Fi or mobile data) and the *Where* as the table writes it ("Production, the TEST machine"); row 2 also needs "wait until after 08:00 the next day".
- **BR1-10** (nit) § 3 `TASK_LABELS`: "Send alerts: overdue countermeasures, improvements ready to verify" is a label of two lists. "Send the morning alerts: overdue countermeasures and improvements ready to verify" reads as one sentence (style B).
- **BR1-11** (nit) § 5.4 path: a tap on *Countermeasure for you* opens the top of the improvement page; the countermeasure card is below the problem and the why-why (S071). Accept for this step, and note it for S071's card (an anchor the path could name later); `sw.js` keeps a fragment (`new URL(path, origin)`).

## Checked and found consistent

- **D1, the widening.** `TICKET_KINDS` / `IMPROVEMENT_KINDS` / `KINDS`, `CHANNELS` per kind, one `_push_to_people` and one `people_at_unit`: right-sized, no generic record-alert layer. `ticket_alert` must switch from `KINDS` to `TICKET_KINDS` (`task_handlers.py:115`), as § 3 says, or an `action_given` payload would pass its kind check and fail later. `should_send` and `_SEND_STATES` stay ticket-only; the improvement handler has its own `should_send_improvement`.
- **Behaviour-neutral for tickets.** `recipients` → `people_at_unit(cur, site_id, [unit_id], AUDIENCE[kind], exclude_ids=…, with_email=…)` keeps the same SQL shape and `ORDER BY p.id`. The tests that prove it: `test_alerts.py::TestFanOut` (`test_a_breakdown_reaches_engineers_the_units_supervisors_and_managers` pins recipients, title, body, urgency, silent, TTL 3600 and tag; `test_the_raiser_with_an_audience_role_is_left_out` the exclude list; `test_a_defect_reaches_engineers_quietly`; `test_every_device_of_a_recipient`; `test_push_off_finds_no_channel`), `TestEscalation::test_still_raised_escalates_to_engineers_and_managers`, the assigned tests (`alerts.assignee` is untouched), and `test_closed_email.py::TestFanOut` for `recipients_with_email`. § 8.3 names only "TestFanOut stays green"; the coder should run `test_alerts.py` and `test_closed_email.py` whole.
- **The scan's transaction and locks (D4).** The handler commits nothing; the worker commits with `mark_done` (`worker.py:130-132`) or rolls back; `mark_failed` runs after the rollback with the back-off (`task_queue.py:57`); a deadlock 1213 is an `OperationalError` that is not a lost connection, so `_task_failed` retries it (`worker.py:137`). Success stores the markers and the `improvement_alert` rows in one commit; any exception loses both; after three failures the task is `failed` and `due_tasks` waits for tomorrow — as § 5.2 says. (6b) then (6c) `FOR UPDATE` in id order matches `improvements.py`'s LOCK ORDER (`:19`) and S070 § 5.6 / S072 § 5.7; no route holds a (6b) row while waiting for another (6b) row; the scan takes no counter, ticket, person, unit or cause lock; its two `UPDATE`s change no foreign-key column; masters.py's cause freeze waits on the scan, never the reverse. No new cycle.
- **The markers (D3) on the schema.** v40 adds `overdue_alert_for DATE` after `due_date` (v38) and `ready_alert_for DATETIME` after `watch_from` (v39); S072's CHECKs are untouched; `ADD COLUMN IF NOT EXISTS` on both; no production row (`1baae21` stops at v35). The S072 D1 point is BR1-02.
- **Recipients by key (D6).** `roles_holding("improvement:read")` = operator, supervisor, technician, engineer, manager and `roles_holding("improvement:verify")` = engineer, manager follow `ROLE_INCLUDES` and S072 § 5.8. `people_at_unit`'s membership-or-`person_units` test equals `unit_ids_for`'s pool rule (`access_core.py:125`), and the two units are the predicate's (`unit_access_condition`, `_visible_condition`). An owner without a login has no `push_subscriptions` row; a storekeeper owner has no `improvement:read`; IT admin has no membership; the lead who left the site has no membership: all four get nothing, the lead still gets the owner's overdue alert (Q3.2 a). The owner and lead are re-read at send time, so an owner changed between the scan and the task gets the alert.
- **D7 TTL.** `IMPROVEMENT_TTL_SECONDS` beside `ALERT_TTL_SECONDS`; `_push_to_people` takes the TTL as a parameter so the ticket path keeps 3600 (the test above pins it).
- **D8.** The alert task writes nothing when push is off; the markers were written by the scan's transaction, so turning push on later sends no backlog. Consistent with S021's "enqueued always".
- **What you will get (§ 5.8).** Lines built from `compute_permissions([role])`, so the page follows `config_rbac.py` (S021 BR2-06). The tests it breaks are the ones § 8.3 lists: `TestYouGet`'s five exact-list tests and `test_nothing_for_other_roles` (the operator gains a line; the storekeeper keeps none), `test_push_api.py:57`, `notifications.spec.js:203` (the technician's exact list) and `:137` (the operator joins the dot list; the e2e seed's operator has a unit, `seed_e2e.py:38`). `showDot` needs no frontend change (`notifications.js:46`).
- **The service worker.** `targetUrl` opens any same-origin path; `/tickets/improvements/:id` is the router's `improvement-detail` (`router/index.js:73`); `sw.js` gains no caching and no fetch handler (§ 1 *Out of scope*).
- **Settings › Background tasks.** `get_tasks` iterates `SCHEDULE` in order (`settings.py:353`), so `tasks[0]` stays `purge_access_log` and `test_worker.py::TestTasksCard` stays green; the new entry shows "08:00".
- **Standards.** ISO 9001 § 10.2.1 (c)/(d) and § 7.4, ISO 55001 § 7.4, TPM focused improvement, ISO 27001 A.5.34 and A.8.3, each in plain words; the clause letters as Plan § 1 cites them.
- **Use on the floor.** No screen changes. Three push texts in style B: a title with the place, a body with the serial, what, and the date in DD-MM-YYYY; the overdue body names the owner because the lead reads the same text; the tag makes the overdue alert replace the given one on the owner's phone. Once per due date and once per watch end: no morning nagging. The operator's new dot is stated and justified in § 5.8.
- **§ 9 Q1–Q3.** Q1 (08:00 IST, one string in `SCHEDULE`), Q2 (the given alert on an owner change, D5) and Q3 (quiet, D7; see BR1-03): none defining.
- **Manual checks.** § 8.4's three browser checks are automated; § 8.5's two rows are real-device (push delivery through FCM, a browser cannot judge), row 1 marked important, row 2 plain. Columns: BR1-09.

## Feedback

- hindrance: the facts file reported `targetUrl` "not found" although the brief cites it at `frontend/public/sw.js:38`; `frontend/public` is not in the *Code folders* setting, so `sw.js` is never searched (read by hand, 1 min). Idea: add `frontend/public` to *Code folders*, or let the tool search a file the brief names with a path.
- hindrance: the facts file says `/api/improvements/<id>/actions` is "called in backend/tests/test_improvements_api.py", but `grep -n actions` finds nothing in that file (a loose route match; 1 run to disprove it).
- waste: the S072 brief (909 lines) needed two reads to get its D11–D16 and § 9, which this brief relies on (about 30k tokens).
