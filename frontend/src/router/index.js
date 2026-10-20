import { createRouter, createWebHistory } from "vue-router";
import EquipmentByCodeView from "../views/EquipmentByCodeView.vue";
import EquipmentDetailView from "../views/EquipmentDetailView.vue";
import EquipmentView from "../views/EquipmentView.vue";
import AssetListPrintView from "../views/AssetListPrintView.vue";
import LabelsPrintView from "../views/LabelsPrintView.vue";
import MastersView from "../views/MastersView.vue";
import NotFoundView from "../views/NotFoundView.vue";
import SettingsView from "../views/SettingsView.vue";
import { authenticated, userPermissions } from "../stores/auth";
import { canOpenRoute, landingPath } from "../stores/navigation";

const routes = [
  { path: "/", redirect: () => landingPath(userPermissions.value) ?? "/equipment" },
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
  if (!authenticated.value || canOpenRoute(to.name, userPermissions.value)) return true;
  const landing = landingPath(userPermissions.value);
  return landing && landing !== to.path ? landing : true;
});

export default router;
