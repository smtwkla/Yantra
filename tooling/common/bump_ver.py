"""Bump the version in the VERSION file.

Usage:
    python tooling/bump_ver.py -M   # major: 1.2.3 -> 2.0.0
    python tooling/bump_ver.py -m   # minor: 1.2.3 -> 1.3.0
    python tooling/bump_ver.py -p   # patch: 1.2.3 -> 1.2.4
"""

import argparse
from pathlib import Path

VERSION_FILE = Path(__file__).resolve().parent.parent.parent / "VERSION"


def main():
    parser = argparse.ArgumentParser(description="Bump version in VERSION file")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-M", "--major", action="store_true", help="Bump major version")
    group.add_argument("-m", "--minor", action="store_true", help="Bump minor version")
    group.add_argument("-p", "--patch", action="store_true", help="Bump patch version (default)")
    args = parser.parse_args()

    if not (args.major or args.minor or args.patch):
        args.patch = True

    if not VERSION_FILE.exists():
        VERSION_FILE.write_text("0.0.0\n")
        print(f"Created {VERSION_FILE}")

    ver = VERSION_FILE.read_text().strip()
    major, minor, patch = (int(x) for x in ver.split("."))

    if args.major:
        major, minor, patch = major + 1, 0, 0
    elif args.minor:
        minor, patch = minor + 1, 0
    else:
        patch += 1

    new_ver = f"{major}.{minor}.{patch}"
    VERSION_FILE.write_text(new_ver + "\n")
    print(f"{ver} -> {new_ver}")


if __name__ == "__main__":
    main()