/**
 * Tests for the CHANGELOG.md parser (S048 § 5).
 */

import { describe, it, expect } from "vitest";
import { parseChangelog } from "../src/utils/changelog";

describe("parseChangelog", () => {
  it("reads two versions in file order, with version, date and items", () => {
    const text = [
      "# What changed in Yantra",
      "",
      "## 0.1.10 — 25-10-2026",
      "- First.",
      "- Second.",
      "",
      "## 0.1.9 — 24-10-2026",
      "- Third.",
    ].join("\n");
    expect(parseChangelog(text)).toEqual([
      { version: "0.1.10", date: "25-10-2026", items: ["First.", "Second."] },
      { version: "0.1.9", date: "24-10-2026", items: ["Third."] },
    ]);
  });

  it("takes an em dash or a hyphen between version and date", () => {
    const [a, b] = parseChangelog("## 0.2.0 - 01-11-2026\n- A.\n## 0.1.9 — 24-10-2026\n- B.");
    expect(a).toMatchObject({ version: "0.2.0", date: "01-11-2026" });
    expect(b).toMatchObject({ version: "0.1.9", date: "24-10-2026" });
  });

  it("skips the title, blank lines, paragraphs and an item before any heading", () => {
    const text = "# Title\n\n- Stray item.\nSome paragraph.\n\n## 0.1.1 — 01-01-2026\nA paragraph.\n- Kept.\n";
    expect(parseChangelog(text)).toEqual([{ version: "0.1.1", date: "01-01-2026", items: ["Kept."] }]);
  });

  it("returns an empty list for empty text, null and a title only", () => {
    expect(parseChangelog("")).toEqual([]);
    expect(parseChangelog(null)).toEqual([]);
    expect(parseChangelog("# What changed in Yantra\n")).toEqual([]);
  });

  it("keeps a heading with no items", () => {
    expect(parseChangelog("## 0.1.11 — 27-10-2026\n")).toEqual([{ version: "0.1.11", date: "27-10-2026", items: [] }]);
  });

  it("keeps markup as text", () => {
    const [entry] = parseChangelog("## 1.0.0 — 01-01-2027\n- A <b>bold</b> claim.");
    expect(entry.items).toEqual(["A <b>bold</b> claim."]);
  });

  it("takes a heading with no dash as the version, with an empty date", () => {
    expect(parseChangelog("## Next version\n- X.")).toEqual([{ version: "Next version", date: "", items: ["X."] }]);
  });

  it("drops a leading v from the version", () => {
    expect(parseChangelog("## v0.1.3 — 16-10-2026")[0].version).toBe("0.1.3");
  });

  it("joins an indented line to the item before it", () => {
    const text = "## 0.1.2 — 01-01-2026\n- A long item that an editor\n  wrapped onto two lines.\n- Next.";
    expect(parseChangelog(text)[0].items).toEqual(["A long item that an editor wrapped onto two lines.", "Next."]);
  });

  it("does not join an indented line that follows a blank line", () => {
    const text = "## 0.1.2 — 01-01-2026\n- One.\n\n  stray\n";
    expect(parseChangelog(text)[0].items).toEqual(["One."]);
  });
});
