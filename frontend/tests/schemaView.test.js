/**
 * Tests for the schema page's pure functions, docs/schema/schema-view.js (S078 § 8.3).  The file is
 * a classic script that sets window.YantraSchemaView; it runs here in a node:vm sandbox.
 */

import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const code = fs.readFileSync(path.join(here, "../../docs/schema/schema-view.js"), "utf8");
const sandbox = { window: {} };
vm.runInNewContext(code, sandbox);
const view = sandbox.window.YantraSchemaView;

function col(name, type, { key = "", nullable = false } = {}) {
  return { name, type, null: nullable, default: null, key, extra: "" };
}

function table(columns, { pk = ["id"], fks = [], indexes = [] } = {}) {
  return { columns, primary_key: pk, foreign_keys: fks, indexes, checks: [] };
}

function fk(name, columns, references, refColumns, required) {
  return { name, columns, references, ref_columns: refColumns, required, on_delete: "RESTRICT", on_update: "RESTRICT" };
}

// Area A: units, equipment, improvements (a unique self link); area B: people, tickets, options,
// values (a two-column key to options); orphans: in no notes entry.
function schema() {
  return {
    migration: 41,
    tables: {
      units: table([col("id", "int", { key: "PK" }), col("name", "varchar(100)")]),
      equipment: table(
        [col("id", "int", { key: "PK" }), col("unit_id", "int", { key: "FK" }),
         col("model_id", "int", { key: "FK", nullable: true }), col("serial", "varchar(40)", { nullable: true })],
        { fks: [fk("fk_equipment_unit", ["unit_id"], "units", ["id"], true)] }),
      improvements: table(
        [col("id", "int", { key: "PK" }), col("follow_up_of_id", "int", { key: "FK,UK", nullable: true }),
         col("lead_id", "int", { key: "FK" })],
        { fks: [fk("fk_improvements_follow_up", ["follow_up_of_id"], "improvements", ["id"], false),
                fk("fk_improvements_lead", ["lead_id"], "people", ["id"], true)],
          indexes: [{ name: "uq_improvements_follow_up", unique: true, columns: ["follow_up_of_id"] }] }),
      people: table([col("id", "int", { key: "PK" }), col("name", "varchar(100)"),
                     col("username", "varchar(100)", { key: "UK", nullable: true })]),
      tickets: table(
        [col("id", "int", { key: "PK" }), col("equipment_id", "int", { key: "FK" }),
         col("reported_by_id", "int", { key: "FK", nullable: true })],
        { fks: [fk("fk_tickets_equipment", ["equipment_id"], "equipment", ["id"], true),
                fk("fk_tickets_reporter", ["reported_by_id"], "people", ["id"], false)] }),
      options: table([col("id", "int", { key: "PK" }), col("property_id", "int")]),
      values: table(
        [col("model_id", "int", { key: "PK" }), col("option_id", "int", { key: "FK", nullable: true }),
         col("property_id", "int", { key: "PK,FK" })],
        { pk: ["model_id", "property_id"],
          fks: [fk("fk_values_option", ["option_id", "property_id"], "options", ["id", "property_id"], false)] }),
      orphans: table([col("id", "int", { key: "PK" }), col("unit_id", "int", { key: "FK" })],
        { fks: [fk("fk_orphans_unit", ["unit_id"], "units", ["id"], true)] }),
    },
  };
}

function notes() {
  return {
    overview_note: "Every table.",
    areas: [{ name: "A", note: "Area A." }, { name: "B", note: "Area B." }],
    tables: {
      units: { area: "A", holds: "Units" },
      equipment: { area: "A", holds: "Equipment" },
      improvements: { area: "A", holds: "Improvements" },
      people: { area: "B", holds: "People" },
      tickets: { area: "B", holds: "Tickets" },
      options: { area: "B", holds: "Options" },
      values: { area: "B", holds: "Values" },
    },
    planned_note: "Not built yet.",
    planned: [],
  };
}

describe("tabs", () => {
  it("puts Overview first, then the areas in notes order", () => {
    expect(view.tabs(notes())).toEqual(["Overview", "A", "B"]);
  });
});

describe("areaTables", () => {
  it("sorts the own tables; a linked table of another area is a neighbour, one linked only to a neighbour is not", () => {
    const parts = view.areaTables(schema(), notes(), "A");
    expect(parts.own).toEqual(["equipment", "improvements", "units"]);
    // tickets points at equipment and improvements at people: neighbours; values and options link
    // only among area B, and orphans has no notes entry: not neighbours
    expect(parts.neighbours).toEqual(["people", "tickets"]);
  });
});

describe("diagramSource for an area", () => {
  const lines = view.diagramSource(schema(), notes(), "A").split("\n");

  it("draws own tables with every column and the base type, neighbours with their PK columns only", () => {
    expect(lines[0]).toBe("erDiagram");
    const start = lines.indexOf("  equipment {");
    expect(lines.slice(start, start + 6)).toEqual([
      "  equipment {", "    int id PK", "    int unit_id FK", '    int model_id FK "null"',
      '    varchar serial "null"', "  }"]);
    const people = lines.indexOf("  people {");
    expect(lines.slice(people, people + 3)).toEqual(["  people {", "    int id PK", "  }"]);
    // own tables by name, then the neighbours by name
    const entities = lines.filter((l) => /^ {2}\w+ \{$/.test(l));
    expect(entities).toEqual(["  equipment {", "  improvements {", "  units {", "  people {", "  tickets {"]);
  });

  it("draws every link with an end in the area, and no link between two neighbours", () => {
    const links = lines.filter((l) => l.includes("--"));
    expect(links).toEqual([
      '  equipment ||--o{ tickets : "equipment_id"',
      '  improvements o|--o| improvements : "follow_up_of_id"',
      '  people ||--o{ improvements : "lead_id"',
      '  units ||--o{ equipment : "unit_id"',
    ]);
    expect(links.some((l) => l.includes("people") && l.includes("tickets"))).toBe(false);
  });
});

describe("link notation", () => {
  const overview = view.diagramSource(schema(), notes(), "Overview");

  it("marks required, optional, one to one and a two-column key", () => {
    expect(overview).toContain('  units ||--o{ equipment : "unit_id"');
    expect(overview).toContain('  people o|--o{ tickets : "reported_by_id"');
    expect(overview).toContain('  improvements o|--o| improvements : "follow_up_of_id"');
    expect(overview).toContain('  options o|--o{ values : "option_id, property_id"');
  });
});

describe("diagramSource for the Overview", () => {
  const lines = view.diagramSource(schema(), notes(), "Overview").split("\n");

  it("shows only keyed columns, every foreign key once, and a table with no notes entry", () => {
    const people = lines.indexOf("  people {");
    expect(lines.slice(people, people + 4)).toEqual(["  people {", "    int id PK", '    varchar username UK "null"', "  }"]);
    expect(lines.filter((l) => l.includes("--"))).toHaveLength(7);
    expect(lines).toContain("  orphans {");
    expect(lines).toContain('  units ||--o{ orphans : "unit_id"');
  });
});

describe("metaLine", () => {
  it("names the migration and the counts", () => {
    expect(view.metaLine(schema())).toBe(
      'Migration v41 · 8 tables, 7 links · PK primary key, FK foreign key, UK unique; "null" = may be empty. ' +
      "A line runs from the parent table to the table that points at it (crow's foot = many).");
  });
});

describe("holdsParts", () => {
  it("reads `a` as code and *b* as italics", () => {
    expect(view.holdsParts("Serial `TK-` per *month*, kept")).toEqual([
      { kind: "text", text: "Serial " }, { kind: "code", text: "TK-" }, { kind: "text", text: " per " },
      { kind: "em", text: "month" }, { kind: "text", text: ", kept" }]);
  });

  it("keeps an unpaired mark and markup as text", () => {
    expect(view.holdsParts("a ` b")).toEqual([{ kind: "text", text: "a ` b" }]);
    expect(view.holdsParts("<b>bold</b> * x")).toEqual([{ kind: "text", text: "<b>bold</b> * x" }]);
    expect(view.holdsParts("")).toEqual([]);
  });
});
