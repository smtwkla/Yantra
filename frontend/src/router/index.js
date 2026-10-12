import { createRouter, createWebHistory } from "vue-router";
import MastersView from "../views/MastersView.vue";
import SettingsView from "../views/SettingsView.vue";
import { authenticated, userPermissions } from "../stores/auth";
import { canOpenRoute, landingPath } from "../stores/navigation";

const routes = [
  { path: "/", redirect: "/masters" },
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
