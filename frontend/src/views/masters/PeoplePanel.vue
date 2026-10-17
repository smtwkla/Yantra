<script setup>
/**
 * Team — the register of people around the machines (S010 A1): direct employees and
 * contractors, each named as a person or a contractor firm, with their trades and an
 * optional Yantra login. Deactivated, never deleted, so old tickets still name them.
 *
 * people:edit maintains the register. The login, and Deactivate / Reactivate of a person
 * who has one, are IT admin's (masters:edit): a login turns a person's roles into access
 * (ISO 27001 A.5.3, A.8.2). The server enforces both; this screen only follows it.
 * Editors see whether a person has a login; only IT admin sees which (the server masks it).
 *
 * Sites and roles (S011 A1): a role per site, with all the site's units or chosen ones. For a
 * person with a login these rows are their Yantra access. The server says which rows the
 * user may change (`editable`) and where a row may be added (`assignable_site_ids`):
 * IT admin any role, an engineer Technician rows at their own site. Rows are saved one by
 * one after the person; the save stops at the first refusal and shows it on that row.
 * A login change (IT admin) sends the whole set with the login, in one request.
 */
import { computed, onMounted, ref } from "vue";
import { apiDelete, apiGet, apiPost, apiPut } from "../../api";
import ActiveToggle from "../../components/ActiveToggle.vue";
import FormModal from "../../components/FormModal.vue";
import { userLogin, userPermissions } from "../../stores/auth";
import { ensureSites, ensureTrades, ensureUnits, sites, trades, units } from "../../stores/masters";
import { describeSiteRow, roleLabel, SITE_ROLES, TECHNICIAN } from "../../utils/siteRoles";
import { useMasterForm } from "./useMasterForm";

const PATH = "/api/masters/people";

const canEdit = computed(() => userPermissions.value.includes("people:edit"));
const canEditLogin = computed(() => userPermissions.value.includes("masters:edit"));
const showInactive = ref(false);
const loadError = ref("");
const people = ref(null);

const rows = computed(() => (people.value ?? []).filter((p) => showInactive.value || p.active));

const EMPLOYMENT_BADGE = { direct: "Direct", contractor: "Contractor" };

// Active trades, plus inactive ones this person already holds, so saving never drops them.
// Fixed when the dialog opens: unticking one by mistake does not make it vanish.
const heldInactiveIds = ref(new Set());
const tradeChoices = computed(() =>
  (trades.value ?? []).filter((t) => t.active || heldInactiveIds.value.has(t.id))
);

// The person being edited (null when adding): its login decides who may (de)activate it
const editing = ref(null);
const canChangeActive = computed(() => canEditLogin.value || !editing.value?.has_login);

async function reload() {
  loadError.value = "";
  try {
    // The pickers (trades, sites, units) are refreshed too: another user may have just added one
    const refresh = { refresh: true };
    const [list] = await Promise.all([
      apiGet(`${PATH}?include_inactive=1`), ensureTrades(refresh), ensureSites(refresh), ensureUnits(refresh),
    ]);
    people.value = list.items;
  } catch (err) {
    loadError.value = err.message;
  }
}

const byId = (a, b) => a - b; // a fixed order, so the dialog's change check compares by value

// --- Site rows ------------------------------------------------------------

const unitsById = computed(() => new Map((units.value ?? []).map((u) => [u.id, u])));
const unitCode = (id) => unitsById.value.get(id)?.code ?? `#${id}`;
const rowText = (row) => describeSiteRow(row, row.unit_ids.map(unitCode));

function rowForm(row) {
  return {
    site_id: row.site_id,
    site_code: row.site_code,
    role: row.role ?? "",
    all_units: row.all_units,
    unit_ids: row.units.map((u) => u.id).sort(byId),
    editable: row.editable,
  };
}

const rowBody = (row) => ({ role: row.role || null, all_units: row.all_units, unit_ids: row.all_units ? [] : row.unit_ids });

// The login the person will have once saved: what IT admin typed, else what the record says
const willHaveLogin = computed(() =>
  canEditLogin.value ? form.value.username.trim() !== "" : Boolean(editing.value?.has_login)
);
// Without a login a person can only be a Technician (S011 A1, gate A); an engineer gives only that
const roleChoices = computed(() =>
  canEditLogin.value && willHaveLogin.value ? SITE_ROLES : SITE_ROLES.filter((r) => r.value === TECHNICIAN)
);

// Units of the row's site: the active ones, plus inactive ones the row already holds
function unitChoices(row) {
  const held = new Set(rowHeldUnits.value.get(row.site_id) ?? []);
  return (units.value ?? []).filter((u) => u.site_id === row.site_id && (u.active || held.has(u.id)));
}
// Fixed when the dialog opens, as the trades above
const rowHeldUnits = ref(new Map());

const addableSites = computed(() => {
  const present = new Set(form.value.sites.map((r) => r.site_id));
  return (editing.value?.assignable_site_ids ?? [])
    .filter((id) => !present.has(id))
    .map((id) => (sites.value ?? []).find((s) => s.id === id))
    .filter(Boolean);
});
const siteToAdd = ref("");

function addSite() {
  const site = (sites.value ?? []).find((s) => s.id === Number(siteToAdd.value));
  if (!site) return;
  form.value.sites = [...form.value.sites, {
    site_id: site.id, site_code: site.code, role: TECHNICIAN, all_units: false, unit_ids: [], editable: true,
  }];
  siteToAdd.value = "";
}

function removeSite(row) {
  form.value.sites = form.value.sites.filter((r) => r !== row);
}

function changeRole(row, role) {
  row.role = role;
  // A manager usually covers the whole site (S011 § 5.3)
  if (role === "maint_manager" && row.unit_ids.length === 0) row.all_units = true;
}

function toggleAllUnits(row) {
  row.all_units = !row.all_units;
  if (row.all_units) row.unit_ids = [];
}

function toggleUnit(row, unitId) {
  const next = new Set(row.unit_ids);
  if (next.has(unitId)) next.delete(unitId);
  else next.add(unitId);
  row.unit_ids = [...next].sort(byId);
}

// IT admin sets or changes a login: the line says what that save grants (A1 rule 1)
const loginChanging = computed(() => {
  if (!canEditLogin.value) return false;
  const login = form.value.username.trim();
  return login !== "" && login !== (editing.value?.username ?? "");
});

// --- Saving -----------------------------------------------------------------

// The login goes in the body only for IT admin, and on an edit only when it changed, so an
// engineer's save never carries it and IT admin can edit their own record (S010 A1 rules 2-3).
// A login change carries the whole set of site rows (S011 A1 rule 1).
function toBody(f) {
  const { sites: siteRows, ...body } = f;
  const login = f.username.trim();
  if (!canEditLogin.value || (editing.value && login === (editing.value.username ?? ""))) {
    delete body.username;
  } else {
    body.username = login === "" ? null : login;
  }
  const loginChanges = "username" in body && (editing.value !== null || body.username !== null);
  if (loginChanges) body.sites = editing.value ? siteRows.map((r) => ({ site_id: r.site_id, ...rowBody(r) })) : [];
  return body;
}

const {
  modal, form, editingId, editingActive, editingLabel, confirmingDeactivate, saving, dirty,
  fieldError, modalError, openCreate, openEdit, send, changeActive,
} =
  useMasterForm({
    path: PATH,
    blank: () => ({ name: "", employment: "direct", username: "", trade_ids: [], sites: [] }),
    fromRecord: (p) => ({
      name: p.name,
      employment: p.employment,
      username: p.username ?? "",
      trade_ids: p.trades.map((x) => x.id).sort(byId),
      sites: (p.sites ?? []).map(rowForm),
    }),
    toBody,
    label: (p) => p.name,
    reload,
  });

// The refusal of one site row: {siteId, message}, shown on that row
const rowError = ref(null);

const sameRow = (before, row) =>
  (before.role ?? "") === row.role && before.all_units === row.all_units
  && before.units.map((u) => u.id).sort(byId).join() === row.unit_ids.join();

// Rows already saved stay saved: reload the person so a retry compares with what the server has
async function refreshEditing(personId) {
  await reload();
  editing.value = (people.value ?? []).find((p) => p.id === personId) ?? editing.value;
}

async function saveRows(personId) {
  const original = new Map((editing.value?.sites ?? []).map((r) => [r.site_id, r]));
  const current = new Set(form.value.sites.map((r) => r.site_id));
  const steps = [];
  for (const [siteId, before] of original) {
    if (before.editable && !current.has(siteId)) steps.push([siteId, () => apiDelete(`${PATH}/${personId}/sites/${siteId}`)]);
  }
  for (const row of form.value.sites) {
    const before = original.get(row.site_id);
    if (!row.editable || (before && sameRow(before, row))) continue;
    steps.push([row.site_id, () => apiPut(`${PATH}/${personId}/sites/${row.site_id}`, rowBody(row))]);
  }
  for (const [siteId, request] of steps) {
    try {
      await request();
    } catch (err) {
      rowError.value = { siteId, message: err.message };
      await refreshEditing(personId);
      err.field = "sites"; // shown on the row, not at the top of the dialog
      throw err;
    }
  }
}

function save() {
  rowError.value = null;
  const body = toBody(form.value);
  return send(async () => {
    const person = editingId.value === null ? await apiPost(PATH, body) : await apiPut(`${PATH}/${editingId.value}`, body);
    if (editingId.value !== null && !("sites" in body)) await saveRows(person.id);
    return person;
  });
}

function add() {
  editing.value = null;
  heldInactiveIds.value = new Set();
  rowHeldUnits.value = new Map();
  rowError.value = null;
  openCreate();
}

function edit(p) {
  editing.value = p;
  heldInactiveIds.value = new Set(p.trades.filter((x) => !x.active).map((x) => x.id));
  rowHeldUnits.value = new Map((p.sites ?? []).map((r) => [r.site_id, r.units.map((u) => u.id)]));
  rowError.value = null;
  siteToAdd.value = "";
  openEdit(p);
}

function toggleTrade(tradeId) {
  const next = new Set(form.value.trade_ids);
  if (next.has(tradeId)) next.delete(tradeId);
  else next.add(tradeId);
  form.value.trade_ids = [...next].sort(byId);
}

onMounted(reload);
</script>

<template>
  <div class="card">
    <div class="card-header d-flex justify-content-between align-items-center">
      <span><i class="fa-solid fa-people-group me-2"></i>Team</span>
      <div class="d-flex align-items-center gap-3">
        <div class="form-check form-switch mb-0">
          <input id="people-inactive" v-model="showInactive" class="form-check-input" type="checkbox" />
          <label class="form-check-label small" for="people-inactive">Show inactive</label>
        </div>
        <button v-if="canEdit" class="btn btn-sm btn-primary" @click="add">
          <i class="fa-solid fa-plus me-1"></i>Add person
        </button>
      </div>
    </div>
    <div class="card-body">
      <div v-if="loadError" class="alert alert-danger">{{ loadError }}</div>
      <div v-if="people === null && !loadError" class="text-secondary">Loading…</div>
      <div v-else-if="rows.length === 0 && !loadError" class="text-secondary">No people yet.</div>
      <div v-else-if="rows.length" class="table-responsive">
        <table class="table table-sm align-middle mb-0">
          <thead>
            <tr>
              <th>Name</th><th>Employment</th><th>Trades</th><th v-if="canEdit">Sites and roles</th>
              <th v-if="canEdit">Login</th><th>Status</th><th v-if="canEdit"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in rows" :key="p.id" :class="{ 'text-secondary': !p.active }">
              <td class="fw-semibold">{{ p.name }}</td>
              <td>
                <span class="badge" :class="p.employment === 'contractor' ? 'text-bg-warning' : 'text-bg-primary'">{{ EMPLOYMENT_BADGE[p.employment] }}</span>
              </td>
              <td>
                <span
                  v-for="x in p.trades"
                  :key="x.id"
                  class="badge text-bg-light border me-1"
                  :class="{ 'opacity-50': !x.active }"
                  :title="x.active ? x.name : `${x.name} (inactive)`"
                >{{ x.name }}</span>
              </td>
              <td v-if="canEdit">
                <div
                  v-for="s in p.sites ?? []"
                  :key="s.site_id"
                  class="text-nowrap"
                  :class="{ 'text-secondary fst-italic': !s.role }"
                  :title="s.all_units ? 'All units' : s.units.map((u) => u.full_code).join(', ')"
                ><span class="fw-semibold">{{ s.site_code }}</span> {{ roleLabel(s.role) }}</div>
              </td>
              <td v-if="canEdit">
                <template v-if="p.username !== undefined">{{ p.username }}</template>
                <i v-else-if="p.has_login" class="fa-solid fa-check text-success" title="Has a Yantra login"></i>
              </td>
              <td><span class="badge" :class="p.active ? 'text-bg-success' : 'text-bg-secondary'">{{ p.active ? "Active" : "Inactive" }}</span></td>
              <td v-if="canEdit" class="text-end text-nowrap">
                <button class="btn btn-sm btn-outline-secondary" title="Edit" @click="edit(p)">
                  <i class="fa-solid fa-pen"></i>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <FormModal ref="modal" :title="editingId === null ? 'Add person' : 'Edit person'" :saving="saving" :dirty="dirty" :error="modalError" @save="save">
    <template v-if="editingId !== null && canChangeActive" #footer-left>
      <ActiveToggle
        :active="editingActive"
        :label="editingLabel"
        :confirming="confirmingDeactivate"
        :disabled="saving"
        @ask="confirmingDeactivate = true"
        @cancel="confirmingDeactivate = false"
        @change="changeActive"
      />
    </template>
    <div class="mb-3">
      <label class="form-label" for="person-name">Name</label>
      <input id="person-name" v-model="form.name" class="form-control" :class="{ 'is-invalid': fieldError('name') }" maxlength="100" />
      <div class="invalid-feedback">{{ fieldError("name") }}</div>
      <div class="form-text">A person, or a contractor firm.</div>
    </div>
    <div class="mb-3">
      <div class="form-label">Employment</div>
      <div class="form-check form-check-inline">
        <input id="person-employment-direct" v-model="form.employment" class="form-check-input" type="radio" value="direct" />
        <label class="form-check-label" for="person-employment-direct">Direct employee</label>
      </div>
      <div class="form-check form-check-inline">
        <input id="person-employment-contractor" v-model="form.employment" class="form-check-input" type="radio" value="contractor" />
        <label class="form-check-label" for="person-employment-contractor">Contractor</label>
      </div>
      <div v-if="fieldError('employment')" class="text-danger small">{{ fieldError("employment") }}</div>
    </div>
    <div class="mb-3">
      <div class="form-label">Trades</div>
      <div v-if="fieldError('trade_ids')" class="alert alert-danger py-2">{{ fieldError("trade_ids") }}</div>
      <div v-if="trades === null" class="text-secondary">Loading…</div>
      <div v-else-if="tradeChoices.length === 0" class="text-secondary">No trades exist yet; add one under Trades.</div>
      <div v-for="t in tradeChoices" :key="t.id" class="form-check" :class="{ 'text-secondary': !t.active }">
        <input :id="`person-trade-${t.id}`" class="form-check-input" type="checkbox" :checked="form.trade_ids.includes(t.id)" @change="toggleTrade(t.id)" />
        <label class="form-check-label" :for="`person-trade-${t.id}`">{{ t.name }}<span v-if="!t.active"> (inactive)</span></label>
      </div>
    </div>
    <div class="mb-3">
      <template v-if="canEditLogin">
        <label class="form-label" for="person-login">Login (optional)</label>
        <input id="person-login" v-model="form.username" class="form-control" :class="{ 'is-invalid': fieldError('username') }" maxlength="100" />
        <div class="invalid-feedback">{{ fieldError("username") }}</div>
        <!-- The user's own login shows the format to type: logins are not checked against Keycloak -->
        <div class="form-text">
          Their Maintenance Team Login ID.<template v-if="userLogin"> Your own login, for ex: <code>{{ userLogin }}</code></template>
        </div>
      </template>
      <template v-else>
        <div class="form-label mb-1">Login</div>
        <div>Has a Yantra login: {{ editing?.has_login ? "yes" : "no" }}</div>
        <div v-if="fieldError('username')" class="text-danger small">{{ fieldError("username") }}</div>
      </template>
    </div>

    <div class="mb-0">
      <div class="form-label">Sites and roles</div>
      <div v-if="editingId === null" class="text-secondary small">Save the person first, then add their sites and roles.</div>
      <template v-else>
        <div v-if="fieldError('sites') && !rowError" class="alert alert-danger py-2">{{ fieldError("sites") }}</div>
        <div v-if="form.sites.length === 0" class="text-secondary small mb-2">No sites.</div>
        <div v-for="row in form.sites" :key="row.site_id" class="border rounded p-2 mb-2">
          <template v-if="row.editable">
            <div class="d-flex align-items-center gap-2 mb-2">
              <strong>{{ row.site_code }}</strong>
              <select
                class="form-select form-select-sm w-auto"
                :aria-label="`Role at ${row.site_code}`"
                :value="row.role"
                @change="changeRole(row, $event.target.value)"
              >
                <option v-if="!roleChoices.some((r) => r.value === row.role)" :value="row.role" disabled>
                  {{ row.role ? roleLabel(row.role) : "Choose a role" }}
                </option>
                <option v-for="r in roleChoices" :key="r.value" :value="r.value">{{ r.label }}</option>
              </select>
              <div class="form-check form-switch mb-0">
                <input :id="`site-${row.site_id}-all`" class="form-check-input" type="checkbox" :checked="row.all_units" @change="toggleAllUnits(row)" />
                <label class="form-check-label small" :for="`site-${row.site_id}-all`">All units</label>
              </div>
              <button type="button" class="btn btn-sm btn-outline-danger ms-auto" title="Remove this site" @click="removeSite(row)">
                <i class="fa-solid fa-xmark"></i>
              </button>
            </div>
            <div class="d-flex flex-wrap gap-3">
              <div v-for="u in unitChoices(row)" :key="u.id" class="form-check mb-0" :class="{ 'text-secondary': !u.active }">
                <input
                  :id="`site-${row.site_id}-unit-${u.id}`"
                  class="form-check-input"
                  type="checkbox"
                  :checked="row.unit_ids.includes(u.id)"
                  :disabled="row.all_units"
                  @change="toggleUnit(row, u.id)"
                />
                <label class="form-check-label small" :for="`site-${row.site_id}-unit-${u.id}`">{{ u.code }}<span v-if="!u.active"> (inactive)</span></label>
              </div>
            </div>
          </template>
          <div v-else class="small">{{ rowText(row) }}</div>
          <div v-if="rowError?.siteId === row.site_id" class="text-danger small mt-1">{{ rowError.message }}</div>
        </div>
        <div v-if="rowError && !form.sites.some((r) => r.site_id === rowError.siteId)" class="text-danger small mb-2">
          {{ rowError.message }}
        </div>
        <div v-if="addableSites.length" class="d-flex gap-2">
          <select v-model="siteToAdd" class="form-select form-select-sm w-auto" aria-label="Site to add">
            <option value="">Add a site…</option>
            <option v-for="s in addableSites" :key="s.id" :value="s.id">{{ s.code }} — {{ s.name }}</option>
          </select>
          <button type="button" class="btn btn-sm btn-outline-primary" :disabled="!siteToAdd" @click="addSite">Add</button>
        </div>
        <div v-if="loginChanging" class="alert alert-warning py-2 mt-2 mb-0 small">
          Adding this login gives access as:
          {{ form.sites.length ? form.sites.map(rowText).join("; ") : "nothing yet (no sites)" }}.
        </div>
      </template>
    </div>
  </FormModal>
</template>
