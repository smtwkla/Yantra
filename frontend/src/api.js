/**
 * API helper — single point for all backend calls.
 *
 * - Injects the Bearer token (refreshed if near expiry) on every request.
 * - No view or component should call fetch() directly.
 */

import { getToken } from "./stores/auth";

async function request(method, url, body = null) {
  const token = await getToken();

  const headers = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  if (body !== null) {
    headers["Content-Type"] = "application/json";
  }

  const options = { method, headers };
  if (body !== null) {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(url, options);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    const err = new Error(error.error || `HTTP ${response.status}`);
    err.status = response.status;
    err.code = error.code ?? null;   // machine-readable refusal kind, when the API sends one
    throw err;
  }

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
