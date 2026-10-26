/**
 * Parser for CHANGELOG.md (S048 § 1, § 1.1).  Pure: text in, plain data out.
 *
 * `## 0.1.10 — 25-10-2026` opens a version block; `- ` lines under it are its items.
 * The output is only text: the dialog shows it through Vue's interpolation, so nothing in the
 * file can become markup.
 */

const HEADING = /^## +(.*)$/;
const SEPARATOR = /\s+[—-]\s+/; // an em dash or a hyphen, with spaces around it

/** `0.1.10 — 25-10-2026` → { version: "0.1.10", date: "25-10-2026" }; a leading "v" is dropped. */
function splitHeading(text) {
  const match = SEPARATOR.exec(text);
  const version = match ? text.slice(0, match.index) : text;
  const date = match ? text.slice(match.index + match[0].length) : "";
  return { version: version.trim().replace(/^v(?=\d)/i, ""), date: date.trim() };
}

/** @returns {{ version: string, date: string, items: string[] }[]} in file order */
export function parseChangelog(text) {
  const versions = [];
  let current = null;
  let lastItemOpen = false; // an indented line may continue the item just before it

  for (const line of String(text ?? "").split(/\r?\n/)) {
    const heading = HEADING.exec(line);
    if (heading) {
      current = { ...splitHeading(heading[1]), items: [] };
      versions.push(current);
      lastItemOpen = false;
    } else if (current && line.startsWith("- ")) {
      current.items.push(line.slice(2).trim());
      lastItemOpen = true;
    } else if (current && lastItemOpen && /^\s+\S/.test(line)) {
      current.items[current.items.length - 1] += ` ${line.trim()}`;
    } else {
      lastItemOpen = false; // a title, a blank line, a paragraph
    }
  }
  return versions;
}
