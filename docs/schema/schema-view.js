// The schema page's pure functions (S078): docs/schema.html draws with them, and
// frontend/tests/schemaView.test.js tests them in a node:vm sandbox.  A classic script, not a
// module: a page opened from disk (file://) may load a classic script by relative path, but
// Chrome refuses a module script file there.  No DOM, no fetch, no storage.
//
// schema: window.YANTRA_SCHEMA (docs/schema/schema.json); notes: window.YANTRA_SCHEMA_NOTES
// (docs/schema/notes.json).  Both are written by tooling\schema-docs.bat write.
(function () {
  "use strict";

  var OVERVIEW = "Overview";

  // Plain code-unit order, as Python's sorted() in the generator: names are lower-case ASCII
  function byText(a, b) {
    return a < b ? -1 : a > b ? 1 : 0;
  }

  function areaNames(notes) {
    return ((notes && notes.areas) || []).map(function (a) { return a.name; });
  }

  // The table's area, or null when it has no notes entry or names an area not in "areas"
  // (the check is red then; the table is drawn only in the Overview).
  function areaOf(notes, table) {
    var entry = notes && notes.tables && notes.tables[table];
    var area = entry ? entry.area : null;
    return areaNames(notes).indexOf(area) >= 0 ? area : null;
  }

  function tabs(notes) {
    return [OVERVIEW].concat(areaNames(notes));
  }

  function sameColumns(a, b) {
    return a.length === b.length && a.every(function (c, i) { return c === b[i]; });
  }

  // Every foreign key as a link from the parent table (referenced) to the child (pointing).
  // One to one when the key's columns alone form a unique key of the child.
  function links(schema) {
    var out = [];
    Object.keys(schema.tables).forEach(function (child) {
      var table = schema.tables[child];
      var uniques = table.indexes.filter(function (ix) { return ix.unique; })
        .map(function (ix) { return ix.columns; })
        .concat([table.primary_key]);
      table.foreign_keys.forEach(function (fk) {
        out.push({
          parent: fk.references,
          child: child,
          label: fk.columns.join(", "),
          required: fk.required,
          oneToOne: uniques.some(function (cols) { return sameColumns(cols, fk.columns); }),
        });
      });
    });
    return out.sort(function (a, b) {
      return byText(a.parent, b.parent) || byText(a.child, b.child) || byText(a.label, b.label);
    });
  }

  function areaTables(schema, notes, area) {
    var names = Object.keys(schema.tables).sort(byText);
    var own = names.filter(function (name) { return areaOf(notes, name) === area; });
    var isOwn = {};
    own.forEach(function (name) { isOwn[name] = true; });
    var near = {};
    links(schema).forEach(function (link) {
      if (isOwn[link.parent] && !isOwn[link.child]) near[link.child] = true;
      if (isOwn[link.child] && !isOwn[link.parent]) near[link.parent] = true;
    });
    var neighbours = Object.keys(near)
      .filter(function (name) { return areaOf(notes, name) !== null; })
      .sort(byText);
    return { own: own, neighbours: neighbours };
  }

  // varchar(100) -> varchar, int unsigned -> int, enum('a','b') -> enum
  function baseType(type) {
    return type.split(/[( ]/)[0];
  }

  function columnLine(column) {
    return "    " + baseType(column.type) + " " + column.name +
      (column.key ? " " + column.key : "") + (column.null ? ' "null"' : "");
  }

  function entityLines(name, columns) {
    return ["  " + name + " {"].concat(columns.map(columnLine), ["  }"]);
  }

  function linkLine(link) {
    return "  " + link.parent + " " + (link.required ? "||" : "o|") + "--" +
      (link.oneToOne ? "o|" : "o{") + " " + link.child + ' : "' + link.label + '"';
  }

  // The Mermaid erDiagram text of a tab: the Overview (every table, keyed columns only, every
  // link), or an area (its own tables with every column, its neighbours with their primary-key
  // columns, every link with at least one end in the area).
  function diagramSource(schema, notes, tab) {
    var lines = ["erDiagram"];
    var all = links(schema);
    if (tab === OVERVIEW) {
      Object.keys(schema.tables).sort(byText).forEach(function (name) {
        var keyed = schema.tables[name].columns.filter(function (c) { return c.key; });
        lines = lines.concat(entityLines(name, keyed));
      });
      return lines.concat(all.map(linkLine)).join("\n");
    }
    var parts = areaTables(schema, notes, tab);
    var inArea = {};
    var drawn = {};
    parts.own.forEach(function (name) {
      inArea[name] = drawn[name] = true;
      lines = lines.concat(entityLines(name, schema.tables[name].columns));
    });
    parts.neighbours.forEach(function (name) {
      var table = schema.tables[name];
      var pk = table.columns.filter(function (c) { return table.primary_key.indexOf(c.name) >= 0; });
      drawn[name] = true;
      lines = lines.concat(entityLines(name, pk));
    });
    // Both ends drawn: a link to a table without notes would make Mermaid draw that table here
    var shown = all.filter(function (link) {
      return (inArea[link.parent] || inArea[link.child]) && drawn[link.parent] && drawn[link.child];
    });
    return lines.concat(shown.map(linkLine)).join("\n");
  }

  function metaLine(schema) {
    var tables = Object.keys(schema.tables).length;
    return "Migration v" + schema.migration + " · " + tables + " tables, " + links(schema).length +
      ' links · PK primary key, FK foreign key, UK unique; "null" = may be empty. ' +
      "A line runs from the parent table to the table that points at it (crow's foot = many).";
  }

  // A holds text in parts: `x` code, *x* italics, everything else text; an unpaired mark stays text.
  function holdsParts(text) {
    var parts = [];
    var pattern = /`([^`]+)`|\*([^*]+)\*/g;
    var last = 0;
    var match;
    function addText(piece) {
      if (!piece) return;
      var prev = parts[parts.length - 1];
      if (prev && prev.kind === "text") prev.text += piece;
      else parts.push({ kind: "text", text: piece });
    }
    while ((match = pattern.exec(text)) !== null) {
      addText(text.slice(last, match.index));
      parts.push(match[1] !== undefined ? { kind: "code", text: match[1] } : { kind: "em", text: match[2] });
      last = pattern.lastIndex;
    }
    addText(text.slice(last));
    return parts;
  }

  window.YantraSchemaView = {
    OVERVIEW: OVERVIEW,
    tabs: tabs,
    areaTables: areaTables,
    diagramSource: diagramSource,
    metaLine: metaLine,
    holdsParts: holdsParts,
  };
})();
