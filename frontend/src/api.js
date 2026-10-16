/**
 * API helper — single point for all backend calls.
 *
 * - Injects the Bearer token (refreshed if near expiry) on every request.
 * - No view or component should call fetch() directly.
 * - Files are fetched as blobs with the token (apiGetBlob), never through a plain
 *   <img src> or link, which could not send it (S006 § 6.3).
 */

import { getToken } from "./stores/auth";

async function authHeaders() {
  const token = await getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// A refusal arrives as {error, field?, code?}; it becomes an Error carrying them
async function throwIfFailed(response) {
  if (response.ok) return;
  const error = await response.json().catch(() => ({ error: response.statusText }));
  const err = new Error(error.error || `HTTP ${response.status}`);
  err.status = response.status;
  err.code = error.code ?? null;   // machine-readable refusal kind, when the API sends one
  err.field = error.field ?? null; // the form field the refusal is about, when the API names one
  throw err;
}

async function request(method, url, body = null) {
  const headers = await authHeaders();
  const options = { method, headers };
  if (body !== null) {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }

  const response = await fetch(url, options);
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
  const response = await fetch(url, { method: "POST", headers: await authHeaders(), body: formData });
  await throwIfFailed(response);
  return response.json();
}

/** GET a file as a Blob, for URL.createObjectURL. */
export async function apiGetBlob(url) {
  const response = await fetch(url, { headers: await authHeaders() });
  await throwIfFailed(response);
  return response.blob();
}
