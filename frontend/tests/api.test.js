import { afterEach, describe, expect, it, vi } from "vitest";

// The auth store pulls in Keycloak; api.js needs only the token and the network-refusal flag
vi.mock("../src/stores/auth", () => ({ getToken: async () => null, networkDenied: { value: null } }));

const { apiGet, apiGetBlob, apiUpload } = await import("../src/api.js");
const { NO_CONNECTION_TEXT, NOT_ANSWERING_TEXT } = await import("../src/utils/messages.js");

function reply(status, body, contentType, statusText = "") {
  return new Response(body, { status, statusText, headers: contentType ? { "Content-Type": contentType } : {} });
}

async function refusal(promise) {
  try {
    await promise;
  } catch (err) {
    return err;
  }
  throw new Error("expected a refusal");
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api.js messages (S064 UX-06)", () => {
  it("a dropped connection is the plain no-connection text with status 0, on every helper", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("Failed to fetch"); }));
    for (const call of [() => apiGet("/api/x"), () => apiUpload("/api/x", new FormData()), () => apiGetBlob("/api/x")]) {
      const err = await refusal(call());
      expect(err.message).toBe(NO_CONNECTION_TEXT);
      expect(err.status).toBe(0);
    }
  });

  it("an abort goes on as it is", async () => {
    const abort = new DOMException("The user aborted a request.", "AbortError");
    vi.stubGlobal("fetch", vi.fn(async () => { throw abort; }));
    expect(await refusal(apiGet("/api/x"))).toBe(abort);
  });

  it("a 502 with an HTML body is the not-answering text", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => reply(502, "<html>Bad Gateway</html>", "text/html", "Bad Gateway")));
    const err = await refusal(apiGet("/api/x"));
    expect(err.message).toBe(NOT_ANSWERING_TEXT);
    expect(err.status).toBe(502);
  });

  it("a 404 without JSON keeps its status text", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => reply(404, "nope", "text/plain", "Not Found")));
    expect((await refusal(apiGet("/api/x"))).message).toBe("Not Found");
  });

  it("a JSON refusal is unchanged: its error, field and code", async () => {
    const body = JSON.stringify({ error: "Choose a unit.", field: "unit_id", code: "x" });
    vi.stubGlobal("fetch", vi.fn(async () => reply(400, body, "application/json")));
    const err = await refusal(apiGet("/api/x"));
    expect([err.message, err.field, err.code, err.status]).toEqual(["Choose a unit.", "unit_id", "x", 400]);
  });

  it("a JSON 503 keeps the server's text", async () => {
    const body = JSON.stringify({ error: "Yantra can't reach its database. Try again in a few minutes." });
    vi.stubGlobal("fetch", vi.fn(async () => reply(503, body, "application/json")));
    expect((await refusal(apiGet("/api/x"))).message).toBe("Yantra can't reach its database. Try again in a few minutes.");
  });
});
