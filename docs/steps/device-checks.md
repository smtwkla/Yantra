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

**Phone set-up for notifications (S021).** Notifications need HTTPS, so their
rows run on production only (the dev server is plain HTTP). Before such a row:
1. On Android, open Yantra in **Chrome**, not Samsung Internet, and tap
   *Install app*.
2. On a Samsung phone, open Settings › Battery › Background usage limits. Check
   that Chrome is not in *Sleeping apps* or *Deep sleeping apps*: a sleeping
   Chrome holds alerts back.
3. On an iPhone (iOS 16.4 or later), open Yantra in Safari, tap *Share › Add to
   Home Screen*, and open it from the icon.
4. In Yantra, tap the **bell** in the top bar (*My notifications*), tap **Turn on
   for this phone**, then **Send a test**.

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
| 9 | S025 | **KLA only — the first release after the squashed schema (v20).** Before it: the two empty tables `equipment_events` and `equipment` are dropped on production (done by KLA on 21-10-2026); optionally trigger db-server's dump first. Run the Release. The deploy waits for `schema_ready` and passes. In Yantra, **Settings › Database** shows the **latest schema version** (this release applies v20 and the versions after it together: v21 of S019, v22 of S020). **Masters** still shows the sites, units, equipment classes and types that were there; the people who had unit access before are now in **Team** with their units (no role yet). If the deploy fails, it prints the rollback lines (S025 § 5.4). | KLA (admin) | Company Wi-Fi (the plant network) | Production | KLA, 23-10-2026: release v0.1.7 deployed, schema ready; Settings › Database shows v25; masters and Team intact |
| 10 | S019 | On an **Android phone** and on an **iPhone**: open a defect ticket (on production, raise one on the TEST machine), press **Schedule**, and tap **Planned date**. The phone's own date picker opens (inside it the phone shows dates its own way, which Yantra does not control). Pick a date a few days ahead, choose *Waiting for parts*, and press **Schedule**. Under the ticket's number the page now shows "for DD-MM-YYYY · waiting for parts", with the date you picked in **DD-MM-YYYY** order. On production, close the ticket afterwards as *Not a fault*. | Dev server: none. Production: a test login with the Engineer role at SMTW (ask KLA) | Company Wi-Fi or home network | Either | |
| 11 | S020 | On an **iPhone** (and, if at hand, an Android phone): open a ticket that is not closed (on production, raise one on the TEST machine), find the **Parts used** card and press **Add part**. Type a description, then tap **Quantity**. The keyboard that opens is the number keyboard with a decimal point (not the full letter keyboard). With the keyboard up, **Save** and **Cancel** stay on the screen, or come back into view by scrolling the dialog or closing the keyboard: say which. Press **Save**; the line shows in the card. On production, remove the line (**Remove**, then **Yes**) and close the ticket as *Not a fault*. | Dev server: none. Production: a test login with the Technician role at SMTW (ask KLA) | Company Wi-Fi or mobile data, either | Either | |
| 12 | S026 | On an **iPhone** (Safari): open any ticket that is back in service or in progress, press **Add labour**, tap a name in the list, leave **Time spent** empty and press **Save**. The dialog scrolls to the red message "Time spent must be between 1 minute and 24 hours" and the cursor is in the hours box. Say whether the keyboard that opens hides the message. (Playwright's WebKit has no on-screen keyboard.) | None | Company Wi-Fi or home network | Dev server | |
| 13 | S027 | On a **Samsung Galaxy** phone: open a ticket that is not closed (on production, raise one on the TEST machine), press **Add note**, and in the *Note* box use **voice typing** (the microphone key on the Samsung keyboard). Say one sentence in **English**, press **Save note**; then add a second note the same way in **Tamil**. Both texts land in the box as spoken and show on the ticket's timeline under *Note*; the Tamil letters show correctly, not as boxes or question marks. On production, close the ticket afterwards as *Not a fault*. | Dev server: none. Production: a test login with the Technician role at SMTW (ask KLA) | Company Wi-Fi or mobile data, either | Either | |
| 14 | S021 | **Important.** **Android phone, Chrome**, set up as in steps 1 and 4 above. Wi-Fi **off**. The test message arrives **with sound**, and tapping it opens Yantra. | A test login with the Engineer role at SMTW (ask KLA) | Mobile data | Production | |
| 15 | S021 | **Important.** **Samsung Galaxy, Chrome**, set up as in steps 1, 2 and 4 above. Leave the phone untouched, screen off, for **at least one hour**. Then the operator test login raises a **breakdown** on the TEST machine (any device, any network). The Samsung phone rings **within a minute**. This proves the battery setting holds. Close the ticket afterwards as *Not a fault*. | A test login with the Engineer role at SMTW (ask KLA); the raise: a test login with the Operator role at SMTW | Mobile data (the phone) | Production, TEST machine | |
| 16 | S021 | **Important.** **iPhone (iOS 16.4 or later)**, KLA's own: step 3 above, log in through the company login page, then step 4. The test message arrives, and tapping it opens Yantra. Do this **from the Home Screen icon only**: in a Safari tab the page explains the Home Screen step instead, which is not a failure. | A test login with the Engineer role at SMTW (ask KLA) | Mobile data | Production | |
| 17 | S021 | **Important.** The engineer's and the supervisor's phones are turned on as in rows 14 and 16, Wi-Fi off. The operator test login raises a **breakdown** on the TEST machine. **Both** phones ring within a minute ("Breakdown · SMTW.MCC2 · …"), and tapping opens **that ticket**. This proves the path from outside the plant. Close the ticket afterwards as *Not a fault*. | Test logins with the Engineer and the Supervisor role at SMTW; the raise: the Operator test login | Mobile data (the phones); the raise: any | Production, TEST machine | |
| 18 | S021 | **Important.** As row 17, the operator test login raises a **defect** (*Running, reduced*). The engineer's phone gets it **without sound** on Android ("Defect · …"); the supervisor's gets nothing. iOS may show it with sound: note what it does. Close the ticket afterwards as *Not a fault*. | As row 17 | Mobile data (the phones); the raise: any | Production, TEST machine | |
| 19 | S021 | **Important.** **IT admin**: in **Settings › Notifications**, set grade **C** (the TEST machine's grade) to **5** minutes and press **Save**. "Saved" shows. (Row 20 follows; IT admin sets C back to 60 after it.) | IT admin | Company network (the plant network) | Production | |
| 20 | S021 | **Important.** The engineer's and the manager's phones on, Wi-Fi off. The operator test login raises a **breakdown** on the TEST machine; nobody touches it. After **about 6 minutes** both phones ring "Not acknowledged after 5 min · …". Then raise a second breakdown and **Acknowledge** it (engineer) within 5 minutes: nothing more arrives for it. IT admin then sets C back to **60**. Close both tickets as *Not a fault*. | Test logins with the Engineer and the Manager role at SMTW; the raise: the Operator test login; IT admin | Mobile data (the phones); IT admin: company network | Production, TEST machine | |
| 21 | S021 | **Important.** **Sign out** on the engineer's phone (the button at the top right). Then the operator test login, on another device, raises a **breakdown** on the TEST machine. The signed-out phone gets **nothing**. Close the ticket afterwards as *Not a fault*. | As row 17 | Any | Production, TEST machine | |
| 22 | S021 | On Android, after *Install app*: the **Yantra icon** (a white Y on dark blue) is on the home screen, and Yantra opens from it **without the browser's address bar**. | A test login with the Engineer role at SMTW (ask KLA) | Any | Production | |
| 23 | S021 | **KLA only, after the deploy.** On a computer, open `<production address>/sw.js` with the browser's developer tools open (Network panel): the answer carries `Cache-Control: no-cache`. In the same panel, open `/manifest.webmanifest` and read its `Content-Type`. If it is `application/octet-stream`, add `types { application/manifest+json webmanifest; }` to `tooling/build/nginx.conf` (a one-line change for the next release). | KLA (any login) | Any | Production | |
| 24 | S021 | From a **computer**, log in as the engineer test login, open *My notifications* and **Remove** the phone in *My devices* (it asks first; press **Yes**). Then the operator test login raises a breakdown on the TEST machine: the phone gets **nothing**. Close the ticket afterwards as *Not a fault*. | As row 17 | Any | Production, TEST machine | |
| 25 | S021 | **Samsung phone, its own browser (Samsung Internet)**: open Yantra there, tap the bell, then **Turn on for this phone**. Note whether it is refused ("This browser cannot get notifications …"). If it is, tell KLA: the server log names the push service, for a one-line change. | A test login with the Engineer role at SMTW (ask KLA) | Any | Production | |
| 26 | S031 | On a phone, open **Me** from the bottom bar and switch the three tabs (*Open work*, *Raised by me*, *My activity*) with your thumb. Each tab opens and shows its list, the three tab buttons are easy to hit, and the page does not scroll sideways. | A test login with the Technician role at SMTW (ask KLA) | Plant Wi-Fi | Production, TEST machine | |
