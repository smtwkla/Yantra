# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Download Google Material Symbols icons as self-hosted SVG files.

    uv run tooling/common/material_icon.py table_edit conveyor_belt --out frontend/src/assets/icons
    uv run tooling/common/material_icon.py conveyor_belt --out icons --style rounded --weight 300 --no-fill --grade -25 --size 20

Each icon is fetched from Google's per-icon SVG endpoint (the one behind
fonts.google.com/icons) and saved as <out>/<name>.svg. The fixed width/height
are removed so CSS decides the size, and fill="currentColor" is set so the icon
takes the surrounding text colour. Committing the files keeps the app offline:
nothing is loaded from Google at run time.

Every icon is downloaded before any file is written, so a typo in one name
leaves the folder untouched. Exit 0: all saved. 1: nothing written (bad name,
existing file without --force, or network error).

Nothing here names a project: the same file works in any repo.
"""
import argparse
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = "https://fonts.gstatic.com/s/i/short-term/release"
TIMEOUT_SECONDS = 20

STYLES = ("outlined", "rounded", "sharp")
WEIGHTS = (100, 200, 300, 400, 500, 600, 700)
GRADES = (-25, 0, 200)
SIZES = (20, 24, 40, 48)  # the optical sizes Google publishes

# Google leaves the default value out of the URL segment (400 / 0 / no fill);
# with all three at default the segment is the word "default".
DEFAULT_WEIGHT = 400
DEFAULT_GRADE = 0

ICON_NAME = re.compile(r"^[a-z0-9_]+$")
SVG_OPEN_TAG = re.compile(r"<svg\b[^>]*>")
SIZE_ATTR = re.compile(r"""\s(?:width|height)=["'][^"']*["']""")
FILL_ATTR = re.compile(r"""\sfill=["'][^"']*["']""")


class IconError(Exception):
    pass


def variant_segment(weight, grade, fill):
    """The URL part that encodes weight, grade and fill, in Google's order."""
    segment = ""
    if weight != DEFAULT_WEIGHT:
        segment += f"wght{weight}"
    if grade != DEFAULT_GRADE:
        # Google spells a negative grade with N: -25 -> gradN25
        segment += f"grad{'N' if grade < 0 else ''}{abs(grade)}"
    if fill:
        segment += "fill1"
    return segment or "default"


def icon_url(name, style, weight, grade, fill, size):
    if not ICON_NAME.match(name):
        raise IconError(f"'{name}' is not an icon name (lowercase letters, digits and _ only, e.g. table_edit)")
    return f"{BASE_URL}/materialsymbols{style}/{name}/{variant_segment(weight, grade, fill)}/{size}px.svg"


def clean_svg(svg):
    """Drop the fixed width/height and colour the icon with currentColor.

    Only the root <svg> tag is touched; viewBox and paths stay as Google drew them.
    """
    match = SVG_OPEN_TAG.search(svg)
    if not match:
        raise IconError("the download is not an SVG")
    tag = SIZE_ATTR.sub("", match.group(0))
    tag = FILL_ATTR.sub("", tag)
    tag = tag[:-1].rstrip() + ' fill="currentColor">'
    return svg[: match.start()] + tag + svg[match.end():]


def download(url, name, style):
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise IconError(f"no icon '{name}' in style '{style}' with these options; "
                            f"check the name on fonts.google.com/icons") from e
        raise IconError(f"{name}: HTTP {e.code} from {url}") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise IconError(f"{name}: could not reach {url} ({e})") from e


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Download Material Symbols icons as SVG files.")
    parser.add_argument("names", nargs="+", help="icon names as on fonts.google.com/icons, e.g. table_edit")
    parser.add_argument("--out", required=True, type=Path, help="folder to save <name>.svg into (created if missing)")
    parser.add_argument("--style", choices=STYLES, default="outlined")
    parser.add_argument("--weight", type=int, choices=WEIGHTS, default=500,
                        help="stroke weight (default 500, about Font Awesome Solid)")
    parser.add_argument("--fill", action=argparse.BooleanOptionalAction, default=True,
                        help="solid icon (default) or --no-fill for outline")
    parser.add_argument("--grade", type=int, choices=GRADES, default=0,
                        help="fine thickness: -25 lighter (for light-on-dark), 0 normal, 200 heavier")
    parser.add_argument("--size", type=int, choices=SIZES, default=24,
                        help="optical size in px: the drawing is tuned for this display size")
    parser.add_argument("--force", action="store_true", help="overwrite icons that already exist")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    targets = {name: args.out / f"{name}.svg" for name in dict.fromkeys(args.names)}
    try:
        existing = [str(path) for path in targets.values() if path.exists()]
        if existing and not args.force:
            raise IconError(f"already exists (use --force to overwrite): {', '.join(existing)}")
        svgs = {}
        for name in targets:
            url = icon_url(name, args.style, args.weight, args.grade, args.fill, args.size)
            svgs[name] = clean_svg(download(url, name, args.style))
    except IconError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    args.out.mkdir(parents=True, exist_ok=True)
    for name, svg in svgs.items():
        targets[name].write_text(svg, encoding="utf-8")
        print(f"saved {targets[name]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
