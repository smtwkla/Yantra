```
Step: S073 — Verified close: screens
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 30-10-2026
```

Reviewed against: 32eb122 + uncommitted S066, S067, S068, S069 (in code review; `improvements.spec.js` is 340 lines); S070–S072 are not coded, so S072 § 6 was read as text, as it stands after S072's round 1.

**Verdict: no `blocker` or `major` is open.** Two `minor` findings, seven nits. Round 2, full
track. No finding needs KLA's decision, and none is defining: both minors are rules the orchestrator
can settle in the brief's text. Facts file read: `scratch/brief-facts-S073.md` (refreshed; it lists
the spec at 340 lines).

**Re-read this round** (the diff `scratch/S073-brief-r1.md` → the brief, `-w`): the header, § 1
(items 1, 2, 3, 6, *After it*), § 2 (the plain-words paragraph), § 3 (`improvementLabels.js` names,
`datetime.js`, `datetime.test.js`, the file count), § 5.1, § 5.2, § 5.3, § 5.5, § 5.6, § 5.7, § 7 D1,
§ 8.1, § 8.2, § 9 and the Review log; and, as asked, S072 § 5.1, § 5.4, § 5.6, § 5.8, § 6 and D3, D13
as they now stand. The unchanged sections (§ 4, § 5.4, § 5.8, § 6, D2–D7, § 8.3, § 8.4) were not
re-reviewed.

**Every round-1 `Accepted` is in the brief's text**, not only in the log: BR1-01 (§ 8.2, line 43 and
the coder's check), BR1-02 (`formatDate`, `watchEndDate`; § 3, § 5.1, § 8.2), BR1-03 (§ 5.6 per
event), BR1-04 (§ 1, § 5.1, § 5.2), BR1-05 (§ 8.1 twice), BR1-06 (b) (every badge, button, line and
test text; "effective" remains only in § 2, the API codes, the help text and the brief's own mode
names), BR1-07 to BR1-16 each at the section the log names.

## Findings

### BR2-01 — minor — § 5.2: the third column's header is wrong on a record closed before its watch ended

**Problem.** The column reads "90 days after" when `watch.ended`, else "41 days so far". S072 § 6
defines `watch.ended` as `now >= until`, from the clock, whatever the state. A record dropped 20
days into its watch (S072 § 5.4 and BR1-14: `end` = `closed_at`, so `after.days` is 20) shows "20
days so far" until the watch's date passes and "90 days after" after it — over 20 days of figures.
"So far" on a dead record is wrong too.

**Why it matters.** The verifier compares like with like (S072 D4); a header that claims 90 days
over 20 misreads the table. The coder would otherwise choose a rule alone.

**Options.**
- (a) **Recommended.** Build the header from `after.days` in every case: "<after.days> days after"
  when `closed` is set or `watch.ended`, else "<after.days> days so far". Closed effective gives
  "90 days after" (its `after.days` is the full watch), a drop mid-watch "20 days after", a running
  watch "41 days so far", a ready one "90 days after". One rule, no special case; `figureRows`
  takes `closed` (or a boolean) as its second argument and the unit test adds the dropped case.
- (b) Keep `watch.ended` and add "(dropped)" to the header on a dropped record. Two rules.

### BR2-02 — minor — § 1, § 5.1, § 5.4: "after the last countermeasure is done" no longer matches S072 D3

**Problem.** S072 BR1-01 (b) changed the rule: the watch starts at the last `done_at` of a
countermeasure of a machine kind (`WATCH_KINDS`: correction, corrective, preventive, design-out);
a *Lesson* or *Spread* done later does not move it (S072 § 5.1 `watch_start`, D3). The brief's
header line "Watch: 90 days after the last countermeasure is done" (§ 1 item 1, § 5.1) and the
*Watch* dialog's help "How long Yantra watches for the failure after the last countermeasure is
done" (§ 5.4) still say the old rule. An engineer who records a *Lesson* done on 25-11 and reads
"Watching since 20-11-2026" will think the date is wrong.

**Why it matters.** The help text is the one place the screen explains the rule; it should state
the rule the backend applies. Scope B: the wording can mislead the user.

**Options.**
- (a) **Recommended.** Keep the header line as it is (plain, and right in the common case) and make
  the help text exact: "How long Yantra watches for the failure after the last fix on the machine is
  done. A lesson or a spread does not move the start. 30 to 365 days; dust builds up over months,
  so 90 is the default." Add one line to § 5.1 saying `watch.from` is S072's `watch_start`
  (machine kinds first), so the coder does not compute a start on the screen.
- (b) Change both texts to "after the last fix on the machine is done". Shorter, but "fix" is a
  new word beside "countermeasure" on the same page.

## Nits

- **BR2-03** (nit) § 3, § 5.6: `EVENT_LABELS` has the same name as `ticketLabels.EVENT_LABELS`
  (`ticketLabels.js:76`); the brief renamed `REMARK_MAX` for that reason (BR1-11). Name it
  `IMPROVEMENT_EVENT_LABELS`, the pattern of `IMPROVEMENT_STATE_LABELS` in the same file.
- **BR2-04** (nit) § 8.1, first important test: after the close the card *Did it come back?* stays
  on the page; add `"Change watch"`, `"Close: it worked"` and `"Did not work — analyse again"` to the
  controls asserted absent (`can_edit_watch` and `can_verify` are false once closed).
- **BR2-05** (nit) § 8.1 `readyImprovement`: name the countermeasure's kind (*Corrective*), so
  `watch_start` takes its `done_at` by S072 § 5.1's first rule and not the fallback; and say the
  repeat ticket gets its symptom the same way (closed through the modes route): a closed ticket
  counts as a repeat (S072 § 5.4, any state, any intensity).
- **BR2-06** (nit) § 5.1, § 1 item 1 (scope B): "Closed 18-02-2027 by Priya (engineer) (the lead):
  did not work" has two bracketed tails in a row. Write "by Priya (engineer), the lead: did not
  work"; the test text in § 8.1 follows.
- **BR2-07** (nit) § 5.4: "while the watch runs" → "once the watch has started (`watch.from` set)":
  a *Ready to verify* page may lengthen the watch (S072 § 5.1's table) and should see the new end
  date too.
- **BR2-08** (nit) § 5.3, § 8.2: line numbers have drifted since round 1 — `MoveDialog.vue` `move`
  is at `:59`, `open(entry)` at `:98`, the 409 watch at `:92-94`; in `improvements.spec.js` the
  `exact: true` "Edit" locators are at `:86` and `:138` (`:25` is "Start improvement", `:58` "Add
  ticket"). § 9's staleness review covers it; cite the names where a parallel step edits the file.
- **BR2-09** (nit) § 5.2 (scope B): "Did not work closes this improvement and starts a new one
  linked to it, with the same tickets." uses the button's name as a noun. Write "*Did not work*
  closes this improvement and starts a new one with the same tickets." (the italics mark the
  button, "linked to it" is what the new page shows anyway).

## Checked and found consistent

- **S072 § 6 as it now stands.** Every field the changed sections read exists: `watch.{days, from,
  until, ended, figures}`, `closed.{at, by_name, by_lead, remark}`, `follow_up_of`, `follow_up`,
  `timeline[].{id, event, occurred_at, by_name, from_state, to_state, ticket, action, remark,
  earlier}`, the four `can_*` flags, `watch_days` on the `PUT`.
- **BR1-01 (b) of S072 on the screens.** `is_open` is computed from the stored state
  (S072 § 5.1), so S068's `canEdit` (`ImprovementDetailView.vue:46`) and the S073 flags hide every
  write control on a closed page, and show them on a *Ready to verify* one (display state, stored
  `watching`). The watch's start comes from the API (`watch.from`); the screen computes only the
  end date (`watchEndDate`), which equals the date part of S072's `watch_until` (`watch_from +
  timedelta(days)`), year end included.
- **Edit lines.** `tickets_core.edit_lines` (`backend/tickets_core.py:735`) writes "Label: old →
  new", so the watch test's "Watch: 90 days → 120 days" (§ 8.1) is the line S072 § 5.6 writes;
  `earlier` is NULL on `edited` and `action_changed`, so § 5.6's "Was:" rule (only when `earlier`
  and `remark` are both set) fires on `why_changed` and `root_cause_changed` alone, as intended.
- **The timeline rule per event (§ 5.6)** matches S072 § 5.6's table: `started` with no ticket and
  one `ticket_linked` per ticket (S072 BR1-05); `action_added`'s remark names the kind and text, so
  the join is shown on `action_done` and `action_cancelled` only; `why_removed` carries `earlier`
  alone.
- **The 400 under the field (§ 8.1, second test).** `FormModal.vue:165` is `novalidate`, so the
  empty remark reaches the server and "Say why it did not work" (S072 § 5.3) shows beside the field
  through `fieldError`, as `RootCauseDialog.vue:69-74` does; `allowFailedRequest` for the 400 is
  in the test as BR1-09 asked.
- **BR1-01's fix.** `ticketRow` (`improvements.spec.js:17`) is the *Tickets* card's `li[data-ticket]`
  and holds the serial as a `router-link` (`ImprovementDetailView.vue:198-202`), so the scoped
  click lands on the ticket page as before. The only other serial-link locator in the spec today is
  `:105`, on the list page, untouched.
- **`readyImprovement` timing.** Ticket 40 days back (admin bypasses `ticket:backdate`), done 35
  days back, `watch_days` 30 → `until` 5 days back → *Ready to verify* through S072's `PUT`
  row ("may become ready"); the first ticket lies in *before* (65–35 days back), a repeat 10 days
  back is `in_watch`. S069's close helper (`improvements.spec.js:196-202`) sets the mode on the
  close, as § 8.1 says.
- **Wording (KLA's delegated decision).** Badges "Closed: it worked" / "Closed: did not work",
  buttons "Close: it worked" / "Did not work — analyse again", submit "Close and analyse again";
  "effective" only in the API codes, § 2 and the help text; S072 D13 matches.
- **File count.** 9 code files (the view, five new components, `improvementLabels.js`,
  `datetime.js`) + 3 test files = 12; `screens.spec.js` runs again.
- **`formatDate` and `watchEndDate`.** `datetime.js` has only `formatDateTime` (`:11`), which adds
  the time for a datetime; `datetime.test.js` has no date-only case: both additions are new, as
  § 3 says, and `datetime.js` is not in the settings' shared list.
- **Locators.** The new names share no substring with the S068/S069 non-exact locators on the
  improvement page; `useShowMore`'s label is "Show all n" (`useShowMore.js:16`).

## Feedback

- idea: the brief anchors by line number in files a parallel step edits (`MoveDialog.vue`,
  `improvements.spec.js`), and the numbers moved between round 1 and round 2 of the same day
  (BR2-08); a rule "anchor by name, not line, in a file another open step touches" would save the
  staleness churn (`docs/steps/README.md` § Stale brief check).
