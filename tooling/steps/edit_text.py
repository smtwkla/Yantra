"""Exact text replace for agents (02-11-2026, KLA's feedback triage): the same mechanical edit in
one or many files, with the texts read from files, so no shell quoting, heredoc or sed mangles a
backslash or a CRLF on the way in.

    python tooling/steps/edit_text.py <file> [<file> …] --old-file old.txt --new-file new.txt [--count N]

Write old.txt and new.txt with the Write tool first. Each file must hold the old text exactly N
times (default 1); else the run refuses and writes no file at all. The texts are taken exactly as
written, a last line break included, except their line endings: they are changed to the file's
own (CRLF or LF), so a text written with LF matches a CRLF file. A file with both CRLF and LF
lines is refused: which ending the new lines should get is a guess. Whether the file ends with a
line break stays as it was. The file is written as UTF-8 without a BOM (a BOM it had is removed,
and the output says so); a file that is not UTF-8 is refused.

Exit 0: every file changed; 1: refused (nothing written); 2: wrong arguments."""

import argparse
import sys
from pathlib import Path

CRLF, LF = "\r\n", "\n"
BOM = "﻿"


class EditError(Exception):
    """A refusal, with a message for the agent."""


def line_ending(text):
    """CRLF or LF, the one ending ``text`` uses (LF when it has no line break); None when mixed."""
    crlf = text.count(CRLF)
    lf = text.count(LF) - crlf
    if crlf and lf:
        return None
    return CRLF if crlf else LF


def with_ending(text, ending):
    return text.replace(CRLF, LF).replace(LF, ending)


def replace_text(content, old, new, count=1):
    """Pure: ``content`` with ``old`` replaced by ``new``, ``count`` times exactly.
    -> (the new content, the 1-based line of each match, the ending used)."""
    if not old:
        raise EditError("the old text is empty")
    ending = line_ending(content)
    if ending is None:
        crlf = content.count(CRLF)
        raise EditError(f"mixed line endings ({crlf} CRLF, {content.count(LF) - crlf} LF); "
                        "make them one kind first")
    old, new = with_ending(old, ending), with_ending(new, ending)
    spots, start = [], 0
    while (at := content.find(old, start)) != -1:
        spots.append(content.count(LF, 0, at) + 1)
        start = at + len(old)
    if len(spots) != count:
        found = "not found" if not spots else f"found {len(spots)} times (lines {', '.join(map(str, spots))})"
        raise EditError(f"the old text was {found}; expected {count}")
    result = content.replace(old, new)
    if content.endswith(LF) and not result.endswith(LF):
        result += ending
    elif not content.endswith(LF) and result.endswith(LF):
        result = result[:-len(ending)]
    return result, spots, ending


def read_text(path, what):
    try:
        return Path(path).read_bytes().decode("utf-8")
    except FileNotFoundError:
        raise EditError(f"{what} {path}: no such file") from None
    except UnicodeDecodeError as error:
        raise EditError(f"{what} {path}: not UTF-8 ({error.reason} at byte {error.start})") from None


def edit_files(files, old, new, count=1):
    """Checks every file first and writes them only when all pass. -> one report line per file."""
    planned = []
    for name in files:
        content = read_text(name, "file")
        had_bom = content.startswith(BOM)
        try:
            result, spots, ending = replace_text(content.removeprefix(BOM), old, new, count)
        except EditError as error:
            raise EditError(f"{name}: {error}") from None
        old_lines, new_lines = with_ending(old, LF).count(LF) + 1, with_ending(new, LF).count(LF) + 1
        report = (f"{name}: replaced {len(spots)} time(s) at line(s) {', '.join(map(str, spots))} "
                  f"({'CRLF' if ending == CRLF else 'LF'}); {old_lines} line(s) became {new_lines}")
        planned.append((name, result, report + ("; BOM removed" if had_bom else "")))
    for name, result, _ in planned:
        Path(name).write_bytes(result.encode("utf-8"))
    return [report for _, _, report in planned]


def main(argv):
    parser = argparse.ArgumentParser(description="Replace an exact text in files; texts read from files.")
    parser.add_argument("files", nargs="+")
    parser.add_argument("--old-file", required=True)
    parser.add_argument("--new-file", required=True)
    parser.add_argument("--count", type=int, default=1, help="how many times the old text must be found")
    args = parser.parse_args(argv)
    if args.count < 1:
        parser.error("--count must be 1 or more")
    try:
        # a text file written by PowerShell or Notepad may start with a BOM: it is no part of the text
        old = read_text(args.old_file, "old text").removeprefix(BOM)
        new = read_text(args.new_file, "new text").removeprefix(BOM)
        for line in edit_files(args.files, old, new, args.count):
            print(line)
    except EditError as error:
        print(f"refused: {error}; no file written")
        return 1
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
