/**
 * Auth store — Keycloak initialisation and reactive auth state.
 *
 * Init sequence:
 *   1. Fetch Keycloak config from /api/auth/config.
 *   2. Init Keycloak with login-required + PKCE.
 *   3. Call /api/auth/me with the Bearer token.
 *   4. Store role and permissions from the response.
 *
 * The frontend never parses the Keycloak token for roles — they come from /api/auth/me.
 */

import { ref } from "vue";
import Keycloak from "keycloak-js";
import { apiGet } from "../api";

// Reactive state — imported directly by components
export const authenticated = ref(false);
export const userName = ref("");
export const userRole = ref("");
export const userRoles = ref([]);
export const userPermissions = ref([]);
export const devBypass = ref(false);
/** Set when login cannot complete — App.vue shows it instead of the spinner. */
export const authError = ref("");

let keycloak = null;

/**
 * Return the current access token, refreshing if needed.
 * Called by api.js before every request.
 */
export async function getToken() {
  if (!keycloak) return null;

  try {
    // Refresh if token expires within 30 seconds
    await keycloak.updateToken(30);
  } catch {
    // Refresh failed — force re-login
    keycloak.login();
    return null;
  }

  return keycloak.token;
}

/**
 * Log out — redirect to Keycloak logout endpoint.
 * In dev bypass mode, just reloads the page.
 */
export function logout() {
  if (keycloak) {
    keycloak.logout();
  } else {
    window.location.reload();
  }
}

/** Fetch the user's profile and permissions from the backend and populate state. */
async function loadProfile() {
  let me;
  try {
    me = await apiGet("/api/auth/me");
  } catch (err) {
    // 401 after a successful Keycloak login = signed in, but holding no Yantra role
    authError.value = err.status === 401
      ? "You are signed in, but your account has no Yantra role. Ask IT to assign one."
      : `Could not load your profile: ${err.message}`;
    return;
  }
  authenticated.value = true;
  userName.value = me.name || me.username;
  userRole.value = me.role;
  userRoles.value = me.roles;
  userPermissions.value = me.permissions;
}

/**
 * Initialise authentication. Called once at app startup.
 */
export async function initAuth() {
  // 1. Fetch Keycloak config from the backend.
  // Direct fetch() — no Bearer token available yet at this point.
  let config;
  try {
    const configRes = await fetch("/api/auth/config");
    if (!configRes.ok) throw new Error("Backend returned " + configRes.status);
    config = await configRes.json();
  } catch (err) {
    authError.value = `Cannot reach the server (${err.message}). Try again shortly.`;
    return;
  }

  // Dev auth bypass — backend signals Keycloak is not needed
  if (config.devBypass) {
    console.warn("Auth bypass: DEV_AUTH_BYPASS enabled on backend.");
    devBypass.value = true;
    await loadProfile();
    return;
  }

  // 2. Init Keycloak
  keycloak = new Keycloak({
    url: config.url,
    realm: config.realm,
    clientId: config.clientId,
  });

  let isAuth;
  try {
    isAuth = await keycloak.init({
      onLoad: "login-required",
      pkceMethod: "S256",
      checkLoginIframe: false,  // Avoid X-Frame-Options errors from Keycloak
    });
  } catch {
    authError.value = "Could not reach the login server. Try again shortly.";
    return;
  }

  if (!isAuth) return;

  // 3–4. Fetch user info from our backend (not from the token)
  await loadProfile();
}
