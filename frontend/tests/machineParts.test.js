import { describe, expect, it, vi } from "vitest";

vi.mock("../src/api", () => ({ apiGet: vi.fn() }));

const { apiGet } = await import("../src/api");
const { keepChoice, loadMachineParts, partRows } = await import("../src/utils/machineParts.js");

const CHILDREN = [
  { id: 2, code: "EXT-GB1", name: "Gearbox", status: "active", children: [
    { id: 3, code: "EXT-GB1-B1", name: "Bearing", status: "active" },
    { id: 4, code: "EXT-GB1-OLD", name: "Old seal", status: "scrapped" },
  ] },
  { id: 5, code: "EXT-M1", name: "Motor", status: "scrapped", children: [
    { id: 6, code: "EXT-M1-F", name: "Fan", status: "active" },
  ] },
];

describe("the machine's parts (S020, from EditTicketDialog)", () => {
  it("lists two levels, the lower one indented, scrapped ones and their parts left out", () => {
    expect(partRows(CHILDREN)).toEqual([
      { id: 2, label: "EXT-GB1 Gearbox" },
      { id: 3, label: "— EXT-GB1-B1 Bearing" },
    ]);
    expect(partRows(undefined)).toEqual([]);
  });

  it("loads them from the machine's equipment detail", async () => {
    apiGet.mockResolvedValueOnce({ id: 1, children: CHILDREN });
    expect(await loadMachineParts(1)).toHaveLength(2);
    expect(apiGet).toHaveBeenCalledWith("/api/equipment/1");
  });

  it("keeps the current choice first when it is not listed (scrapped since)", () => {
    const rows = [{ id: 2, label: "EXT-GB1 Gearbox" }];
    expect(keepChoice(rows, { id: 4, code: "EXT-GB1-OLD", name: "Old seal" })).toEqual([
      { id: 4, label: "EXT-GB1-OLD Old seal" }, ...rows,
    ]);
    expect(keepChoice(rows, { id: 2, code: "EXT-GB1", name: "Gearbox" })).toBe(rows);
    expect(keepChoice(rows, null)).toBe(rows);
  });
});
