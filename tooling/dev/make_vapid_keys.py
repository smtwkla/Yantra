"""Print a fresh VAPID key pair for web push (S021 § 3, § 5.6) as the three lines to paste into
backend/secrets_app.py — for dev, and once for production.

    uv run --project backend python tooling/dev/make_vapid_keys.py [mailto:address]

Production's pair is made once and never rotated casually: a new pair silently ends every
phone's subscription, and each phone must turn notifications on again.  The private key is a
secret (ISO 27001 A 8.24): it goes into secrets_app.py only, never into the repo or a chat.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "backend"))

from vapid_keys import make_key_pair  # noqa: E402  (the backend folder, added above)

DEFAULT_SUBJECT = "mailto:it@smtw.in"


def main():
    subject = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SUBJECT
    if not subject.startswith("mailto:"):
        sys.exit("The subject must be a mailto: address, e.g. mailto:it@smtw.in")
    public, private = make_key_pair()
    print(f'VAPID_PUBLIC_KEY = "{public}"')
    print(f'VAPID_PRIVATE_KEY = "{private}"')
    print(f'VAPID_SUBJECT = "{subject}"')


if __name__ == "__main__":
    main()
