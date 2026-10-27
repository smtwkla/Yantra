/**
 * API helper — single point for all backend calls.
 *
 * - Injects the Bearer token (refreshed if near expiry) on every request.
 * - No view or component should call fetch() directly.
 * - Files are fetched as blobs with the token (apiGetBlob), never through a plain
 *   <img src> or link, which could not send it (S006 § 6.3).
 * - The browser's own texts never reach the user (S064 UX-06): a dropped connection and a 5xx
 *   without JSON (the proxy's error page) get plain messages.
 */

import { getToken, networkDenied } from "./stores/auth";
import { NO_CONNECTION_TEXT, NOT_ANSWERING_TEXT } from "./utils/messages";

// fetch() rejects with a TypeError when the network fails ("Failed to fetch", "Load failed");
// it becomes a plain Error with status 0.  An abort (AbortError) is the caller's and goes on as it is.
async function send(url, options) {
  try {
    return await fetch(url, options);
  } catch (cause) {
    if (!(cause instanceof TypeError)) throw cause;
    // A TypeError is mostly the network, but a coding error (bad header value) looks the same
    console.error("fetch failed", cause);
    const err = new Error(NO_CONNECTION_TEXT, { cause });
    err.status = 0;
    err.code = null;
    err.field = null;
    err.ip = null;
    throw err;
  }
}

// A body that is not JSON: a 5xx is the proxy or a crashed server; a 4xx keeps its status text
function notJsonBody(response) {
  return { error: response.status >= 500 ? NOT_ANSWERING_TEXT : response.statusText };
}

async function authHeaders() {
  const token = await getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// A refusal arrives as {error, field?, code?, ip?}; it becomes an Error carrying them.
// "network_denied" on any call (IT admin off the plant network, S013) also sets the auth
// store's networkDenied, so App.vue shows the full-page card even mid-session.
async function throwIfFailed(response) {
  if (response.ok) return;
  const error = await response.json().catch(() => notJsonBody(response));
  const err = new Error(error.error || `HTTP ${response.status}`);
  err.status = response.status;
  err.code = error.code ?? null;   // machine-readable refusal kind, when the API sends one
  err.field = error.field ?? null; // the form field the refusal is about, when the API names one
  err.ip = error.ip ?? null;       // the address the server saw, on a network refusal
  if (err.code === "network_denied") networkDenied.value = { message: err.message, ip: err.ip };
  throw err;
}

async function request(method, url, body = null) {
  const headers = await authHeaders();
  const options = { method, headers };
  if (body !== null) {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }

  const response = await send(url, options);
  await throwIfFailed(response);

  const ct = response.headers.get("content-type") || "";
  if (response.status === 204 || !ct.includes("application/json")) return null;
  return response.json();
}

export function apiGet(url) {
  return request("GET", url);
}

export function apiPost(url, body) {
  return request("POST", url, body);
}

export function apiPut(url, body) {
  return request("PUT", url, body);
}

export function apiDelete(url) {
  return request("DELETE", url);
}

/** POST a multipart form; the browser sets the Content-Type with its boundary. */
export async function apiUpload(url, formData) {
  const response = await send(url, { method: "POST", headers: await authHeaders(), body: formData });
  await throwIfFailed(response);
  return response.json();
}

/** GET a file as a Blob, for URL.createObjectURL. */
export async function apiGetBlob(url) {
  const response = await send(url, { headers: await authHeaders() });
  await throwIfFailed(response);
  return response.blob();
}
