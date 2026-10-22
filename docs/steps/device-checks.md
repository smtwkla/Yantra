# Checks on a real device

The checks a browser test cannot do: a real camera, paper from a printer and a
ruler, a phone's own keyboard, a real login. Everything else is checked by the
browser tests (`tooling/run-e2e-tests.bat`, S024). This file is the master list;
the rules are in [README.md](README.md) § Manual checks.

**How it works.** KLA hands the rows to the person doing them (today **IT
Admin**), printed or by chat. She does each row and tells KLA what she saw. KLA
tells the planner, who fills in *Done* (`IT Admin, DD-MM-YYYY`) and ticks the
check in the step's report. Nobody else edits this file. A done row stays here
as the record.

**Where a row runs:**
- **Dev server**: Yantra on KLA's laptop, `http://<KLA's laptop>:5176` (KLA
  gives the address). It can be reached only while the laptop is on the company
  or home network. There is no login on it: it opens straight away.
- **Production, TEST machine**: the real Yantra address (ask KLA), on the
  machine named **TEST** in unit `SMTW.MCC2`, label marked TEST. Its code:
  `________` (written here once KLA has created it). Never use a real machine:
  its tickets would count in the breakdown history and the KPIs. After a check,
  close any ticket it made as *Not a fault*.
- **Either**: whichever is at hand.

**Accounts.** On production, use the test login named in the row (ask KLA for
it). Never the IT admin account for a check about another role, and never the
IT admin account on mobile data: it is refused off the plant network (S013).
On the dev server, and for print or measure rows, no account is needed.

## After each deploy (production only, once per release)

These test the deployment, not a step's code, so they can only run on
production.

| # | What to do, and what you should see | Account | Network | Where | Done |
|---|---|---|---|---|---|
| D1 | On a phone, open Yantra's address. The company login page (Keycloak) appears; log in. Yantra opens, and the top bar shows your name. (S011) | A test login with the Technician role at SMTW (ask KLA) | Company Wi-Fi | Production | |
| D2 | Android phone, Wi-Fi **off**: point the camera at the TEST machine's QR label and open the link it shows. Yantra asks for the login if needed, then shows the TEST machine's page (its code and name at the top). (S014) | A test login with the Technician role at SMTW (ask KLA) | Mobile data | Production, TEST machine | |
| D3 | The same as D2 with an **iPhone's** camera. (S014) | A test login with the Technician role at SMTW (ask KLA) | Mobile data | Production, TEST machine | |

## Open checks by step

| # | Step | What to do, and what you should see | Account | Network | Where | Done |
|---|---|---|---|---|---|---|
| 1 | S014 | Equipment list: tick a few machines, press **Print labels**, print the sheet on the office printer at **100 %** ("Actual size", not "Fit to page"). Measure one square with a ruler: it is **52 mm** on each side. | None | Company Wi-Fi (the office printer) | Dev server | |
| 2 | S014 | Take a printed label, rub a finger of grease across one corner (or crumple it a little), then point a phone's camera at it. The phone still reads the code and offers the link. | None | Company Wi-Fi or home network | Dev server | |
| 3 | S015 | Equipment list › **Print asset list**, switch on **Checklist columns**, print one unit on A4 **portrait** at **100 %**. On the paper: no column is cut off at the right edge, the *Remarks* column is wide enough to write in, and the signature lines are on the sheet. | None | Company Wi-Fi (the office printer) | Dev server | |
| 4 | S015 | Print the asset list of a unit with enough machines for **two pages** (on the dev server, ask KLA to add machines first; production's real units are long enough). On page 2 the table's header row repeats at the top, and the next unit starts on a new page. | Dev server: none. Production: a test login with the Engineer role at SMTW (ask KLA) | Company Wi-Fi (the office printer) | Either | |
| 5 | S017 | On a phone: open the equipment page (the TEST machine on production), **Raise ticket**, choose *Early signs*, write "Device check", Save. Press **Add photos**: the phone offers the **camera** as well as the gallery. Take a photo with the camera, then **Done**. The ticket page shows the photo's thumbnail. On production, close the ticket afterwards as *Not a fault*. | Dev server: none. Production: a test login with the Operator role at SMTW (ask KLA) | Company Wi-Fi or home network | Either | |
| 6 | S018 | On an **Android phone**: open a ticket that is *Back in service* and has labour (KLA prepares one), press **Close**, then **Add remark** and tap the remark box so the keyboard comes up. **Close ticket** and **Cancel** stay on the screen (or come back into view by scrolling the dialog). | None | Company Wi-Fi or home network | Dev server | |
| 7 | S018 | The same as row 6 on an **iPhone**. iOS lays the keyboard over the page, so the buttons may sit under it: say whether you can still reach **Close ticket** and **Cancel** (by scrolling the dialog or closing the keyboard). | None | Company Wi-Fi or home network | Dev server | |
| 8 | S016, S017, S018 | On an **iPhone**: open **Raise ticket**, choose *Running, reduced*, leave the description empty, press **Save**. The red message "Describe the problem, or pick a symptom" shows under the description field. Then, on a ticket, press **Not a fault** and **Save** with no remark. The message "Add a remark" shows under the remark box. (Playwright's WebKit found a fault here that Chrome did not; this confirms it is gone on the real browser.) | None | Company Wi-Fi or home network | Dev server | |
| 9 | S025 | **KLA only — the first release after the squashed schema (v20).** Before it: the two empty tables `equipment_events` and `equipment` are dropped on production (done by KLA on 21-10-2026); optionally trigger db-server's dump first. Run the Release. The deploy waits for `schema_ready` and passes. In Yantra, **Settings › Database** shows the **latest schema version** (this release applies v20 and the versions after it together: v21 of S019, v22 of S020). **Masters** still shows the sites, units, equipment classes and types that were there; the people who had unit access before are now in **Team** with their units (no role yet). If the deploy fails, it prints the rollback lines (S025 § 5.4). | KLA (admin) | Company Wi-Fi (the plant network) | Production | |
| 10 | S019 | On an **Android phone** and on an **iPhone**: open a defect ticket (on production, raise one on the TEST machine), press **Schedule**, and tap **Planned date**. The phone's own date picker opens (inside it the phone shows dates its own way, which Yantra does not control). Pick a date a few days ahead, choose *Waiting for parts*, and press **Schedule**. Under the ticket's number the page now shows "for DD-MM-YYYY · waiting for parts", with the date you picked in **DD-MM-YYYY** order. On production, close the ticket afterwards as *Not a fault*. | Dev server: none. Production: a test login with the Engineer role at SMTW (ask KLA) | Company Wi-Fi or home network | Either | |
| 11 | S020 | On an **iPhone** (and, if at hand, an Android phone): open a ticket that is not closed (on production, raise one on the TEST machine), find the **Parts used** card and press **Add part**. Type a description, then tap **Quantity**. The keyboard that opens is the number keyboard with a decimal point (not the full letter keyboard). With the keyboard up, **Save** and **Cancel** stay on the screen, or come back into view by scrolling the dialog or closing the keyboard: say which. Press **Save**; the line shows in the card. On production, remove the line (**Remove**, then **Yes**) and close the ticket as *Not a fault*. | Dev server: none. Production: a test login with the Technician role at SMTW (ask KLA) | Company Wi-Fi or mobile data, either | Either | |
