import { createRouter, createWebHistory } from "vue-router";
import EquipmentByCodeView from "../views/EquipmentByCodeView.vue";
import EquipmentDetailView from "../views/EquipmentDetailView.vue";
import EquipmentView from "../views/EquipmentView.vue";
import AssetListPrintView from "../views/AssetListPrintView.vue";
import LabelsPrintView from "../views/LabelsPrintView.vue";
import MastersView from "../views/MastersView.vue";
import MeView from "../views/MeView.vue";
import NotFoundView from "../views/NotFoundView.vue";
import NotificationsView from "../views/NotificationsView.vue";
import ReadingsView from "../views/ReadingsView.vue";
import RaiseTicketView from "../views/RaiseTicketView.vue";
import SettingsView from "../views/SettingsView.vue";
import TicketDetailView from "../views/TicketDetailView.vue";
import TicketsView from "../views/TicketsView.vue";
import { authenticated, userPermissions } from "../stores/auth";
import { canOpenRoute, homePath, landingPath } from "../stores/navigation";

const routes = [
  // "/" shows nothing and is sent to the landing page by the guard below, or by App.vue once the
  // permissions arrive: a redirect decided here would run before login, with no permissions.
  { path: "/", name: "home", component: { render: () => null } },
  {
    path: "/equipment",
    name: "equipment",
    component: EquipmentView,
    meta: { title: "Equipment" },
  },
  {
    path: "/equipment/:id(\\d+)",
    name: "equipment-detail",
    component: EquipmentDetailView,
    meta: { title: "Equipment" },
  },
  // The link on a QR label (S014): the code, never the internal id
  {
    path: "/e/:code([A-Za-z0-9]{1,12})",
    name: "equipment-by-code",
    component: EquipmentByCodeView,
    meta: { title: "Equipment" },
  },
  // Tickets (S017). Only the list is a nav item; for /tickets/new and /tickets/:id the API's
  // 403 / 404 is the gate, and the buttons that lead there are hidden by permission (BR1-10)
  {
    path: "/tickets",
    name: "tickets",
    component: TicketsView,
    meta: { title: "Tickets" },
  },
  {
    path: "/tickets/new",
    name: "ticket-new",
    component: RaiseTicketView,
    meta: { title: "Raise ticket" },
  },
  {
    path: "/tickets/:id(\\d+)",
    name: "ticket-detail",
    component: TicketDetailView,
    meta: { title: "Ticket" },
  },
  // Readings (S040, S050): the end-of-day sheet for reading:log holders, the register for every equipment:read holder
  {
    path: "/readings",
    name: "readings",
    component: ReadingsView,
    meta: { title: "Readings" },
  },
  // Me (S031): my open work, tickets I raised, my activity; the first nav item (S035)
  {
    path: "/me",
    name: "me",
    component: MeView,
    meta: { title: "Me" },
  },
  {
    path: "/labels",
    name: "labels",
    component: LabelsPrintView,
    meta: { title: "QR labels" },
  },
  {
    path: "/asset-list",
    name: "asset-list",
    component: AssetListPrintView,
    meta: { title: "Asset list" },
  },
  {
    path: "/masters",
    name: "masters",
    component: MastersView,
    meta: { title: "Masters" },
  },
  // My notifications (S021): from the bell in the top bar, not a nav item; push:subscribe is
  // every logged-in role's, and the "no access yet" screen has no top bar route to it
  {
    path: "/notifications",
    name: "notifications",
    component: NotificationsView,
    meta: { title: "My notifications" },
  },
  {
    path: "/settings",
    name: "settings",
    component: SettingsView,
    meta: { title: "Settings" },
  },
  // Last, so every route above wins
  { path: "/:pathMatch(.*)*", name: "not-found", component: NotFoundView, meta: { title: "Page not found" } },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// A route the user's permissions do not cover (typed URL, bookmark) goes to
// the first page they may see. Before login completes nothing renders;
// App.vue re-checks once permissions arrive.
router.beforeEach((to) => {
  if (to.name === "home" && authenticated.value) return homePath(userPermissions.value);
  if (!authenticated.value || canOpenRoute(to.name, userPermissions.value)) return true;
  const landing = landingPath(userPermissions.value);
  return landing && landing !== to.path ? landing : true;
});

export default router;
