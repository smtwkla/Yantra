# Yantra Help: the screenshot list

The Help source is in `help/` (see `help/README.md`). This file is not published: it sits beside the
apps, so the gallery skips it. It has three parts: the guide's shots (who, where, the how-to lines), the
table *slide id → shot → alt text* that a retake follows, and the Documents and photos page's shots.

The tour (`tooling/help-shots.bat`) writes the shots to `scratch/help-shots/shots/` (PNG) and `scratch/help-shots/webp/` (lossless WebP). Phone shots: Pixel 7 at scale 2 (824 px wide). Desktop shots: 1366×768 at scale 1.5.
"Full" means a long page taken whole (the phone's bottom bar then sits over the page's end).
Data: standard plant data on a throw-away test database (SMTW and BRICKS sites; machines from Plant-Facts and the dev seed).
People are the test seed's made-up ones: Muthu (operator), Selvi (supervisor), Kannan and Ravi (technicians), Priya (engineer), Arun (manager), IT admin, Admin.
The top bar shows the person with the role in brackets, e.g. "Kannan (technician)". History lines show logins such as `e2e_operator` (test logins).

Order below is the suggested teaching order.

---

## 1. Getting around

### 01-me-open-work-phone.png — Me › Open work (`/me`)
- **Who / where:** technician (Kannan), phone on the floor.
- The first screen after login. **PM jobs** and **Tickets** given to you, most urgent first.
- Tap a row to open the PM job or the ticket.
- The bottom bar: **Me**, **Equipment**, **Tickets**, **PM**, **Readings**. The bell at the top opens your notifications.

### 02-me-operator-phone.png — Me › Raised by me (`/me`)
- **Who / where:** operator (Muthu), phone.
- Tap **Raised by me** to see the tickets you raised and their state (Raised, Acknowledged, In progress, Back in service…).
- **My activity** lists what you did.

### 03-me-engineer-desktop.png — Me on the desktop (`/me`)
- **Who / where:** engineer (Priya), office desktop.
- On a desktop the menu is the dark bar on the left (same items, plus **Masters** and **Settings** for those who may use them).
- The engineer's open work: here a **Countermeasure** to do, with **Mark done**.

---

## 2. Equipment

### 10-equipment-list-phone.png — Equipment list on the phone (`/equipment`)
- **Who / where:** operator, phone.
- Type in **Code, name, model, class or notes** to find a machine. **Filters** narrows the list.
- The dot shows open tickets: red = breakdown, yellow = defect, green = none.

### 13-equipment-list-desktop.png — Equipment list (`/equipment`)
- **Who / where:** engineer, desktop.
- Filters across the top: **All sites**, **All units**, **All classes**, **Any lifecycle**, **Any criticality**, **Any ticket status**, **Any contract status**; **Filter by property**; **Show scrapped**.
- Tick rows, then **Print labels (n)**. **Print asset list** prints a stock-check list. **Add equipment** adds a machine.

### 14-equipment-search-desktop.png — Search (`/equipment`)
- Type "compressor" in the search box. The list shows only matching machines.
- Click the code (e.g. **CMP002**) to open the machine.

### 11-qr-landing-phone.png — Scan a QR label (`/e/<code>`)
- **Who / where:** anyone, phone, at the machine.
- Scan the QR label with the phone camera. Yantra opens that machine's page straight away.
- Tap **Raise ticket** to report a problem on this machine.

### 12-equipment-detail-phone.png — Machine page on the phone (`/equipment/<id>`, full)
- **Who / where:** operator, phone.
- Top: code, name, **In service**, criticality (**A**). Big red **Raise ticket** button.
- Cards: **Open tickets**, **PM plans**, **Documents**, **Photos**, **Details**, and further down **Meters** and **History**.

### 15-equipment-detail-desktop.png — Machine page (`/equipment/<id>`, full)
- **Who / where:** engineer, desktop. Main extruder.
- Buttons: **Raise ticket**, **Edit**, **Add part**, **Move**, **Change lifecycle**, **Print label**.
- Cards: **Lessons** (**Add lesson**), **Under contract**, **Open tickets**, **PM plans** (**Add PM plan**), **Details**, **Properties**, **Parts**, **Meters** (**Open register**, **Add meter**, **Log reading**), **History**, **Documents**, **Photos**.

### 16-component-unit-desktop.png — A part of a machine (`/equipment/<id>`, full)
- **Who / where:** engineer, desktop. GBX001 Extruder main gearbox, a part of EXT001.
- The path at the top (SMTW › MCC2 › EXT001 › GBX001) shows which machine it belongs to.
- A part has its own tickets and PM plans (here **Gearbox oil change**).

### 17-labels-print-desktop.png — QR labels (`/labels?ids=…`)
- **Who / where:** engineer or IT admin, desktop.
- On the Equipment list, tick the machines, click **Print labels (n)**. This page opens in a new tab.
- Click **Print**. Print at **100 %** ("Actual size"), on plain A4. Check one square with a ruler.

### 18-asset-list-print-desktop.png — Asset list (`/asset-list`)
- **Who / where:** engineer or manager, desktop.
- Click **Print asset list** on the Equipment list. One table per unit, ready for a stock check.
- **Include parts** and **Checklist columns** change what is printed. Then click **Print**.

---

## 3. Tickets (breakdowns and defects)

### 20-raise-ticket-pick-machine-phone.png — Raise ticket: pick the machine (`/tickets/new`)
- **Who / where:** operator, phone.
- Tap **Tickets**, then **Raise ticket**. Type part of the name ("compressor") and tap the machine.
- Quicker: scan the machine's QR label and tap **Raise ticket** there.

### 21-raise-ticket-filled-phone.png — Raise ticket: describe it (`/tickets/new`, full)
- Under **How bad is it?** tap one: **Stopped** (breakdown), **Running, reduced** or **Early signs** (defects).
- Pick the **Symptom (if you know it)**. Write **What is wrong?**. Check **When did it happen?**.
- Already put it right yourself? Tick **Already fixed — back in service**.
- Tap **Save ticket**.

### 22-tickets-list-phone.png — Tickets list on the phone (`/tickets`)
- **Who / where:** technician, phone.
- Red rows are breakdowns, yellow rows are defects. The clock shows how long it is open.
- Filters: **Open**, **Breakdowns and defects**, **All sites**, **All units**, **Assigned to me**.

### 25-tickets-list-desktop.png — Tickets list (`/tickets`)
- **Who / where:** engineer, desktop.
- Same list and filters. **Overdue since …** marks a ticket on hold past its planned date.
- **Raise ticket** at the right. The **Improvements** tab is next to **Tickets**.

### 23-ticket-detail-phone.png — A ticket on the phone (`/tickets/<id>`, full)
- **Who / where:** technician, phone. A breakdown in progress.
- The next step is the big blue button (**Back in service**). Also **Add note**, **Change severity**, **Put on hold**.
- The contract line shows the machine is under AMC. Cards: **Details**, **Times**, **Assigned**, and below **Timeline**.

### 24-ticket-back-in-service-dialog-phone.png — Back in service (dialog)
- Tap **Back in service** when the machine runs again.
- Check **Back in service at** (or keep **Now**). Under **Who did the work?** tap the person.
- Tap **Back in service** to save.

### 26-ticket-detail-desktop.png — A ticket waiting to be closed (`/tickets/<id>`, full)
- **Who / where:** engineer, desktop. Ticket back in service.
- Buttons: **Send back** (not fixed), **Close**, **Add note**, **Start improvement**, **Not fixed — raise again**.
- Cards: **Details**, **Times**, **Assigned** (**Assign**), **Meters**, **Parts used** (**Add part**), **Timeline**, **Documents**, **Photos**, **Labour** (**Add labour**).

### 27-ticket-close-dialog-desktop.png — Close a ticket (dialog)
- Click **Close**. Check the **Symptom**; choose the **Cause** and the **Action taken**.
- Labour must be entered first. Parts fitted? Cancel and add them on the ticket first.
- Click **Close ticket**. The ticket becomes read-only.

### 28-ticket-assign-dialog-desktop.png — Assign (dialog)
- **Who / where:** engineer or supervisor, desktop.
- On a ticket, click **Assign** in the **Assigned** card. Type a name or vendor to filter, click the person.
- Click **Assign**. The person gets a notification.

### 29-ticket-on-hold-desktop.png — A ticket on hold (`/tickets/<id>`)
- **Who / where:** engineer, desktop.
- A ticket put on hold shows **Deferred**, its planned date and the reason (here: waiting for a production slot or shutdown).
- Buttons: **Start work**, **Fixed**, **Add note**, **Change severity**, **Change plan**.

---

## 4. Improvements (root-cause analysis)

### 33-start-improvement-dialog-desktop.png — Start improvement (dialog)
- **Who / where:** engineer, desktop.
- On a ticket that keeps coming back, click **Start improvement**.
- Fill **Title**, **Problem**, and choose the **Lead**. Click **Start improvement**.

### 30-improvements-list-desktop.png — Improvements list (`/tickets/improvements`)
- **Who / where:** engineer or manager, desktop.
- Tickets › **Improvements** tab. Filters: **Open improvements**, **All units**.
- **Print register** opens the register for the management review.

### 31-improvement-detail-desktop.png — An improvement (`/tickets/improvements/<id>`, full)
- **The problem** and **Tickets (2)** (**Add ticket**): what happened and the loss.
- **Why-why**: click **Add why** until the answer is something the plant can change. Then **Edit root cause**.
- **Countermeasures**: **Add countermeasure**, each with a kind (Correction, Preventive, Design-out…), owner and due date. The owner clicks **Mark done**.
- **Timeline** keeps every change. **Add note** adds a remark.

### 32-improvement-register-desktop.png — Improvement register (`/tickets/improvements/register`)
- **Who / where:** manager, desktop.
- Choose the period (**From**, **To**). The register counts improvements by state and lists each one.
- Click **Print**.

---

## 5. One-point lessons

### 35-lesson-page-phone.png — A one-point lesson (`/equipment/lessons/<id>`, full)
- **Who / where:** operator, phone, at the machine.
- Open the machine, tap the lesson in the **Lessons** card. Read the photo and the steps.
- "for every Compressor": the lesson shows on every machine of that class. **Print lesson** prints it for the machine.

### 36-lesson-page-desktop.png — The same lesson on the desktop
- **Who / where:** engineer, desktop.
- To write one: on the machine page, click **Add lesson** in the **Lessons** card.

---

## 6. Meter readings

### 40-readings-sheet-phone.png — Readings › Sheet (`/readings`, full)
- **Who / where:** operator, phone, end of shift.
- Tap **Readings**. Each machine of your units with its meters; the last reading is under the name.
- Type each value. Keep **Now** ticked, or untick it and set the **Time of reading**.
- Tap **Save readings**.

### 41-log-reading-dialog-phone.png — Log reading (dialog)
- On a machine page, tap **Log reading** beside a meter.
- Type the **Value**. Tick **Meter reset** only when the meter was replaced or set back to zero.
- Tap **Save**.

### 42-readings-register-desktop.png — Readings › Register (`/readings?tab=register`)
- **Who / where:** engineer, desktop.
- On a machine page click **Open register**, or pick a machine on the **Register** tab.
- All readings of the machine, newest first; **Meters: All** picks one meter.

---

## 7. Preventive maintenance (PM)

### 60-pm-plan-desktop.png — PM plan (`/equipment/pm/<id>`, full)
- **Who / where:** engineer, desktop.
- On the machine page click **Add PM plan** (or a plan's name to change it).
- **Plan**: **Title**, **Done by**, **Assign jobs to**, **An engineer verifies each job**.
- **When is it due?**: **By calendar: every** … and/or **By meter: every** … ; **Last done**.
- **Items** on the right; **Add item**; arrows change the order. Click **Save plan**.

### 61-pm-add-item-dialog-desktop.png — Add item (dialog)
- Click **Add item**. Choose **Task**, **Check** or **Reading**.
- Write **What to do or check**; add **Help text** if useful; choose **Photo** (none, optional, required).
- A reading can log a meter and has Min and Max. Click **Save item**.

### 62-pm-new-plan-desktop.png — New PM plan (`/equipment/<id>/pm/new`, full)
- An empty plan for Screw compressor 2: fill the title, tick the trigger, add at least one item, **Save plan**.

### 50-pm-list-due-phone.png — PM › Due (`/pm`)
- **Who / where:** technician, phone.
- Tap **PM**. Tabs: **Due**, **Upcoming**, **To verify**, **Done**. Badges: **Overdue**, **Due**, **In progress**, **Sent back**.
- **Assigned to me** shows only your jobs. Tap a job to open it.

### 51-pm-job-before-start-phone.png — A PM job, not started (`/pm/jobs/<id>`, full)
- Check **Performed by** and **Started** (keep **Now**).
- Tap **Start job**. Before that the items are only shown.

### 52-pm-job-filling-phone.png — Filling the items (full)
- For a check tap **OK**, **Not OK** or **NA**. For a task tap **Done** or **Not done**.
- **Not OK** asks **What is wrong?**: type it and tap **Save**.
- Each answer is saved at once ("Saved").

### 53-pm-job-filled-phone.png — All items filled (full)
- For a reading type the value and tap **Save**. A reading tied to a meter is also logged as a meter reading.
- When it says "4 of 4 filled", tap **Mark job done**.

### 54-pm-mark-done-dialog-phone.png — Mark job done (dialog)
- Check the **Done** time (keep **Now**). You cannot change the job afterwards unless an engineer sends it back.
- Tap **Mark job done**.

### 55-pm-job-sent-back-phone.png — A job sent back (full)
- **Sent back** badge and the engineer's remark in the yellow box ("Belt is still loose…").
- Do the work again, change the answers, tap **Mark job done**.

### 63-pm-jobs-due-desktop.png — PM › Due (`/pm`)
- **Who / where:** engineer, desktop. All due, overdue and started jobs, with filter **All my units** and **Assigned to me**.

### 64-pm-jobs-upcoming-desktop.png — PM › Upcoming (`/pm?tab=upcoming`)
- Jobs coming due soon (here the gearbox oil change).

### 65-pm-jobs-to-verify-desktop.png — PM › To verify (`/pm?tab=to_verify`)
- Finished jobs waiting for an engineer. "1 Not OK" warns that a check failed.

### 66-pm-jobs-done-desktop.png — PM › Done (`/pm?tab=done`)
- Closed jobs: **Verified**, **On time** / late, **Skipped**.

### 67-pm-job-to-verify-desktop.png — A job to verify (`/pm/jobs/<id>`, full)
- **Who / where:** engineer, desktop.
- Read each result (Not OK rows are red). Then **Verify job** or **Send back**.

### 68-pm-verify-dialog-desktop.png — Verify job (dialog)
- Add a **Remark (optional)**. Click **Verify job**. The job closes and cannot be changed or sent back.

### 69-pm-send-back-dialog-desktop.png — Send back job (dialog)
- Write **What must be done again?**. Click **Send back job**. The job goes back to In progress for the technician.

### 70-pm-reschedule-dialog-desktop.png — Reschedule job (dialog)
- On a due job, card **Reschedule or skip**, click **Reschedule job**.
- Set the **New due date**, write **Why is the job moved?**, click **Reschedule job**.

### 71-pm-skip-dialog-desktop.png — Skip job (dialog)
- Click **Skip job**. Write **Why is the job skipped?**. Click **Skip job**.
- The job counts as not done; the next job counts from today. You cannot undo this.

### 72-pm-job-verified-desktop.png — A verified job (full)
- Who did it, when, and **Verified by** with the remark. **History** at the bottom.

### 73-pm-job-skipped-desktop.png — A skipped job
- **Skipped** badge with the reason and who skipped it.

---

## 8. Contracts (AMC, warranty)

### 80-contract-page-desktop.png — A contract (`/contracts/<id>`, full)
- **Who / where:** manager, desktop.
- **Terms**: vendor, period, covered and not covered, response time, call-out number, cost note.
- **Machines covered**: **Add machine**, **Edit price**, **Remove**. **Renew contract** at the top right.
- **Breakdown calls**: tickets the vendor's engineer worked on, with "N of 4 calls used".
- Only managers see the price, the cost note, the documents and the photos.

### 81-contract-card-on-machine-desktop.png — Under contract card on a machine (`/equipment/<id>`)
- On the machine page: **Under contract** shows the vendor, the end date (**Ends in 45 days**), what is covered and the **Call-out number**. **Open contract** opens it.

### 85-masters-contracts-desktop.png — Masters › Contracts
- **Who / where:** manager or admin, desktop. All contracts with filters; **Add contract**.

---

## 9. Masters (set-up lists)

All on the desktop, as admin (some tabs also for the engineer). Click **Masters** in the left bar, then a tab.

### 85-masters-sites-desktop.png — Sites
- The plant's sites. **Add site**; the pencil edits one.

### 85-masters-units-desktop.png — Units
- Areas or lines inside a site (SMTW.MCC1, SMTW.MCC2, …). **Add unit**.

### 85-masters-classes-desktop.png — Classes
- Kinds of equipment (CMP Compressor, EXT Extruder, …). The code starts each machine's code. **Add class**.

### 85-masters-models-desktop.png — Models
- Maker and model (Atlas Copco GA37, …) with class and type. A model's meters and properties pass to every machine of that model. **Add model**.

### 85-masters-meter-types-desktop.png — Meter types
- Run hours, Oil temperature, … with unit and kind (Counter, Gauge, Amount per period). **Add meter type**.

### 85-masters-failure-codes-desktop.png — Failure codes
- Three lists: **Modes** (symptoms), **Causes**, **Actions** (ISO 14224). **Add mode**.

### 85-masters-trades-desktop.png — Trades
- Mechanical, Electrical, Welding, Instrumentation. Labour is booked per trade. **Add trade**.

### 85-masters-vendors-desktop.png — Vendors
- Outside firms (Atlas Copco service). Link a vendor's engineer as a contractor in Team. **Add vendor**.

### 85-masters-team-desktop.png — Team
- Every person: employment (Direct, Contractor), trades, **Sites and roles**, login. **Add person**.
- A person's role at each site decides what they see and may do.

---

## 10. Settings and notifications

### 90-notifications-phone.png — My notifications (`/notifications`)
- **Who / where:** anyone, phone. Open it from the bell.
- **This device**: turn on notifications for this phone. **My devices**, **Email**, **What you will get**.
- (In the screenshot the test browser blocks notifications, so it says "Notifications are blocked".)

### 91-notifications-desktop.png — My notifications on the desktop
- **Who / where:** manager. Shows the email address from the login and **Send test email**, and the list of alerts a manager gets.

### 95-settings-admin-desktop.png — Settings (`/settings`, full)
- **Who / where:** admin, desktop.
- **Database** status, **Uploads** (largest file), **Labels** (label link address), **Network** (plant network ranges), **Notifications** (escalation minutes per criticality), **Background tasks**, **Access log**.
- Each section has its own **Save**.

### 96-settings-it-admin-desktop.png — Settings as IT admin (`/settings`)
- **Who / where:** IT admin, desktop. Same page; IT admin looks after uploads, labels and the network.

---

## Slide id → shot → alt text

The guide's `<img src>` is `shots/<name>.webp`; a retake replaces the file of the same name.
Slide `cover` and `x12` show one shot twice (the second picture is the same file moved up).

| Slide id | Shot (`help/guide/shots/<name>.webp`) | Alt text |
|---|---|---|
| `cover` | `50-pm-list-due-phone` | The PM jobs list on a phone |
| `x01` | `01-me-open-work-phone` | Me page, open work, on a phone |
| `x02` | `02-me-operator-phone` | Me page, raised by me, on a phone |
| `x03` | `03-me-engineer-desktop` | Me page on the desktop |
| `x13` | `13-equipment-list-desktop` | Equipment list on the desktop |
| `x14` | `14-equipment-search-desktop` | Equipment search |
| `x10` | `10-equipment-list-phone` | Equipment list on a phone |
| `x11` | `11-qr-landing-phone` | The page a QR label opens |
| `x12` | `12-equipment-detail-phone` | Machine page on a phone, top |
| `x12` | `12-equipment-detail-phone` | Machine page on a phone, lower part |
| `x15` | `15-equipment-detail-desktop` | Machine page on the desktop, whole page |
| `x16` | `16-component-unit-desktop` | A component's page |
| `x17` | `17-labels-print-desktop` | QR label sheet |
| `x18` | `18-asset-list-print-desktop` | Asset list for printing |
| `x20` | `20-raise-ticket-pick-machine-phone` | Raise ticket, picking the machine |
| `x21` | `21-raise-ticket-filled-phone` | Raise ticket form, top |
| `x21` | `21-raise-ticket-filled-phone` | Raise ticket form, lower part |
| `x22` | `22-tickets-list-phone` | Tickets list on a phone |
| `x25` | `25-tickets-list-desktop` | Tickets list on the desktop |
| `x23` | `23-ticket-detail-phone` | Ticket on a phone, top |
| `x23` | `23-ticket-detail-phone` | Ticket on a phone, lower part |
| `x24` | `24-ticket-back-in-service-dialog-phone` | Back in service dialog |
| `x26` | `26-ticket-detail-desktop` | Ticket page on the desktop |
| `x27` | `27-ticket-close-dialog-desktop` | Close ticket dialog |
| `x28` | `28-ticket-assign-dialog-desktop` | Assign dialog |
| `x29` | `29-ticket-on-hold-desktop` | Ticket on hold |
| `x33` | `33-start-improvement-dialog-desktop` | Start improvement dialog |
| `x30` | `30-improvements-list-desktop` | Improvements list |
| `x31` | `31-improvement-detail-desktop` | Improvement page, whole |
| `x32` | `32-improvement-register-desktop` | Improvement register |
| `x35` | `35-lesson-page-phone` | One-point lesson on a phone |
| `x36` | `36-lesson-page-desktop` | One-point lesson on the desktop |
| `x40` | `40-readings-sheet-phone` | Readings sheet, top |
| `x40` | `40-readings-sheet-phone` | Readings sheet, lower part |
| `x41` | `41-log-reading-dialog-phone` | Log reading dialog |
| `x42` | `42-readings-register-desktop` | Readings register |
| `x60` | `60-pm-plan-desktop` | PM plan page |
| `x61` | `61-pm-add-item-dialog-desktop` | Add item dialog |
| `x62` | `62-pm-new-plan-desktop` | New PM plan |
| `x50` | `50-pm-list-due-phone` | PM jobs list on a phone |
| `x51` | `51-pm-job-before-start-phone` | PM job before start |
| `x52` | `52-pm-job-filling-phone` | Filling a PM job, top |
| `x52` | `52-pm-job-filling-phone` | Filling a PM job, lower part |
| `x53` | `53-pm-job-filled-phone` | PM job filled, top |
| `x53` | `53-pm-job-filled-phone` | PM job filled, lower part |
| `x54` | `54-pm-mark-done-dialog-phone` | Mark job done dialog |
| `x55` | `55-pm-job-sent-back-phone` | Sent back job, top |
| `x55` | `55-pm-job-sent-back-phone` | Sent back job, lower part |
| `x63` | `63-pm-jobs-due-desktop` | PM jobs, Due tab |
| `x64` | `64-pm-jobs-upcoming-desktop` | PM jobs, Upcoming tab |
| `x65` | `65-pm-jobs-to-verify-desktop` | PM jobs, To verify tab |
| `x66` | `66-pm-jobs-done-desktop` | PM jobs, Done tab |
| `x67` | `67-pm-job-to-verify-desktop` | A PM job to verify |
| `x68` | `68-pm-verify-dialog-desktop` | Verify job dialog |
| `x69` | `69-pm-send-back-dialog-desktop` | Send back job dialog |
| `x70` | `70-pm-reschedule-dialog-desktop` | Reschedule job dialog |
| `x71` | `71-pm-skip-dialog-desktop` | Skip job dialog |
| `x72` | `72-pm-job-verified-desktop` | A verified PM job |
| `x73` | `73-pm-job-skipped-desktop` | A skipped PM job |
| `x80` | `80-contract-page-desktop` | Contract page |
| `x81` | `81-contract-card-on-machine-desktop` | Under contract card |
| `x85contracts` | `85-masters-contracts-desktop` | Masters, Contracts tab |
| `mt4` | `85-masters-models-desktop` | Masters, Models |
| `mt6` | `16-component-unit-desktop` | A component's page |
| `m1` | `85-masters-sites-desktop` | Masters, Sites |
| `m1` | `85-masters-units-desktop` | Masters, Units |
| `m1` | `85-masters-classes-desktop` | Masters, Classes |
| `m1` | `85-masters-models-desktop` | Masters, Models |
| `m2` | `85-masters-meter-types-desktop` | Masters, Meter types |
| `m2` | `85-masters-failure-codes-desktop` | Masters, Failure codes |
| `m2` | `85-masters-trades-desktop` | Masters, Trades |
| `m2` | `85-masters-vendors-desktop` | Masters, Vendors |
| `x85team` | `85-masters-team-desktop` | Masters, Team |
| `x90` | `90-notifications-phone` | My notifications on a phone |
| `x91` | `91-notifications-desktop` | My notifications on the desktop |
| `x95` | `95-settings-admin-desktop` | Settings page, whole |
| `x96` | `96-settings-it-admin-desktop` | Settings as IT admin |

---

## Documents and photos page

Taken by `frontend/help-tour/documents.tour.js` (the tour's third project). The tour uploads a small PDF and a
drawn photo through the real dialogs (`tooling/help/make_photo.py` makes them), so the rows are real. Copy the
`doc-*.webp` files into `help/documents/shots/`.

| Shot (`help/documents/shots/<name>.webp`) | Who / where | What it shows | Used in section |
|---|---|---|---|
| `doc-01-models-documents-button-desktop` | engineer, desktop | Masters › Models, the paperclip button on each row | 4 |
| `doc-02-model-add-document-dialog-desktop` | engineer, desktop | Add document dialog of a model, file chosen, title filled | 4 |
| `doc-03-model-documents-desktop` | engineer, desktop | the model's Documents and Photos cards with the new manual | 4 |
| `doc-04-machine-documents-empty-phone` | engineer, phone | a machine's Documents card with no own document yet; the model's manual shows under From model … | 1 |
| `doc-05-add-document-dialog-phone` | engineer, phone | Add document dialog on a machine | 2 |
| `doc-06-machine-documents-phone` | engineer, phone | own documents, then the group From model … | 2 |
| `doc-07-document-more-actions-phone` | engineer, phone | the More actions menu: Edit title, Remove | 5 |
| `doc-08-remove-document-confirm-phone` | engineer, phone | “Remove this document?” with Yes and No | 5 |
| `doc-09-add-photo-dialog-phone` | engineer, phone | Add photo dialog | 3 |
| `doc-10-machine-photos-phone` | engineer, phone | the Photos card with one photo | 3 |
| `doc-11-removed-documents-desktop` | IT admin, desktop | Settings › Removed documents with a removed document | 6 |
| `doc-12-removed-delete-confirm-desktop` | IT admin, desktop | “Delete for good? The file cannot be recovered.” | 6 |
