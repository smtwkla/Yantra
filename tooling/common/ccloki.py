#!/usr/bin/env python3
"""ccloki.py - restricted read-only Loki wrapper for Claude Code diagnostics.

Claude Code must use this tool (never raw curl) to read fleet logs from the
Loki log store. It enforces, in code, what would otherwise be convention:

  - HTTP GET only - there is no argument that selects another method, so the
    tool is physically incapable of pushing, deleting or flushing log data
  - authenticates with the pre-provisioned READ basic-auth pair; the
    credential is read from a file and never appears on a command line,
    in the request log, or in any output of this tool
  - only Loki's query endpoints are reachable; the endpoint is chosen by the
    verb, so no argument can steer a request at /push or /delete
  - result size is bounded by default (--limit) so a careless selector cannot
    dump the whole store into a terminal
  - HTTPS certificates (if the endpoint is ever fronted by TLS) are pinned by
    SHA-256 fingerprint
  - every request is echoed before execution and appended to the same
    per-machine log ccssh.py uses for this host

The store is fronted by nginx with two basic-auth pairs: a WRITE pair scoped
to /loki/api/v1/push (Alloy only) and a READ pair for the query endpoints.
This tool is given the READ pair - it cannot authenticate against push.

There is exactly one log store, so there is no machine list and no alias
argument. Config and credential live in ONE file, OUTSIDE all repos:

  ~/.claude/prod-vm/loki.conf   key = value lines, '#' comments:
                                  url         http://host:port or https://host:port
                                              (the nginx auth front, not loki:3100)
                                  auth        <read_user>:<password>, or a ready-made
                                              'Authorization: Basic <base64>'
                                  cert_sha256 optional; https:// endpoints only
                                Keep it mode 0600 - it holds the password.
  ~/.claude/logs/prod-vm/loki.cc.log
                                request log, shared with ccssh.py's log for the
                                same host, so ssh and query access read as one
                                timeline.

Usage:
  ccloki.py show                             show the configured store (no secrets)
  ccloki.py scan                             cert fingerprint for pinning (https only)
  ccloki.py labels [-m R]                    label names in the window
  ccloki.py values [-m R] <label>            values of one label
  ccloki.py series [-m R] <selector>         streams matching a selector
  ccloki.py stats  [-m R] <selector>         line/byte count BEFORE fetching
  ccloki.py logs   [-m R] <logql>            fetch log lines
  ccloki.py query  [-m R] <logql>            metric query (rate/count_over_time)

Examples:
  ccloki.py values -m "what is shipping" host
  ccloki.py stats  -m "size the fetch" '{host="db-server"}' --since 24h
  ccloki.py logs   -m "dump job failures" '{host="db-server",unit="mariadb-dump.service"}' --since 24h
  ccloki.py logs   -m "kernel OOM check" '{host="db-server",transport="kernel"} |= "oom"' --since 7d
  ccloki.py query  -m "error rate" 'sum by (host) (count_over_time({job="journal"} |= "error" [1h]))'

Fleet label set (Alloy), deliberately low-cardinality - matchers are EXACT:
  host       short hostname on every stream (e.g. db-server), never the FQDN
  job        journal | docker | dpkg
  unit       systemd unit (job="journal" only), e.g. mariadb-dump.service
  transport  stdout | journal | syslog | kernel | audit | driver (journal only)
  container  docker container name, leading "/" stripped (job="docker" only)
  filename   /var/log/dpkg.log (job="dpkg" only)

Quote the selector in single quotes - it contains {} and " which every shell
mangles otherwise.

This script is synced across repos from smtw-common (see sync_common.py);
it holds no site-specific values.
"""

import argparse
import base64
import hashlib
import http.client
import json
import re
import ssl
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

CONFIG_DIR = Path.home() / ".claude" / "prod-vm"
CONF_FILE = CONFIG_DIR / "loki.conf"
# Named for the machine, not the tool: ccssh.py logs to <alias>.cc.log and the
# store's alias in vms.tsv is "loki", so both land in one per-machine timeline.
LOG_FILE = Path.home() / ".claude" / "logs" / "prod-vm" / "loki.cc.log"

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
URL_RE = re.compile(r"^(https?)://([A-Za-z0-9._-]+):(\d{2,5})$")
FPRINT_RE = re.compile(r"^[0-9a-f]{64}$")
DURATION_RE = re.compile(r"^(\d+)([smhdw])$")

CONF_KEYS = ("url", "auth", "cert_sha256")

# Loki's own default cap (max_entries_limit_per_query); asking for more just
# earns a 400 from the server, so refuse locally with a clearer message.
MAX_LIMIT = 5000
DEFAULT_LIMIT = 200

DURATION_SECS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}

# Query endpoints only. The verb picks the key; no argument reaches this dict,
# so /loki/api/v1/push and /loki/api/v1/delete are unreachable by construction.
ENDPOINTS = {
    "labels": "/loki/api/v1/labels",
    "values": "/loki/api/v1/label/{label}/values",
    "series": "/loki/api/v1/series",
    "stats": "/loki/api/v1/index/stats",
    "range": "/loki/api/v1/query_range",
    "instant": "/loki/api/v1/query",
}

CONF_HELP = (f"Create {CONF_FILE} with (one 'key = value' per line):\n"
             "  url  = http://<loki-host>:3100\n"
             "  auth = <read_user>:<password>\n"
             "See tooling/common/example_loki.conf in the smtw-common repo.")


def die(msg: str):
    print(f"ccloki: error: {msg}", file=sys.stderr)
    sys.exit(2)


def load_conf() -> dict:
    """Parse loki.conf into {scheme, host, port, auth, fingerprint}."""
    if not CONF_FILE.exists():
        die(f"config not found: {CONF_FILE}\n{CONF_HELP}")
    values = {}
    for lineno, line in enumerate(CONF_FILE.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep:
            die(f"{CONF_FILE}:{lineno}: expected 'key = value'")
        # Split on the FIRST '=' only: base64 padding and passwords may contain it.
        key, value = key.strip().lower(), value.strip()
        if key not in CONF_KEYS:
            die(f"{CONF_FILE}:{lineno}: unknown key '{key}' "
                f"(known: {', '.join(CONF_KEYS)})")
        if key in values:
            die(f"{CONF_FILE}:{lineno}: duplicate key '{key}'")
        if not value:
            die(f"{CONF_FILE}:{lineno}: empty value for '{key}'")
        values[key] = value

    for required in ("url", "auth"):
        if required not in values:
            die(f"{CONF_FILE}: missing '{required}'\n{CONF_HELP}")

    m = URL_RE.match(values["url"])
    if not m:
        die(f"{CONF_FILE}: invalid url '{values['url']}' "
            "(must be http://host:port or https://host:port)")
    fprint = values.get("cert_sha256", "-").lower().replace(":", "")
    if fprint != "-" and not FPRINT_RE.match(fprint):
        die(f"{CONF_FILE}: cert_sha256 must be 64 hex chars")
    return {"scheme": m.group(1), "host": m.group(2), "port": int(m.group(3)),
            "auth": values["auth"], "fingerprint": fprint}


def auth_header(auth: str) -> tuple:
    """Return (header_name, header_value) from the configured credential.

    Accepts a ready-made 'Authorization: ...' value, or a bare 'user:password'
    which is base64-encoded here - so the secret never has to be encoded by
    hand and never reaches a command line.
    """
    if auth.lower().startswith("authorization:"):
        name, _, value = auth.partition(":")
        return name.strip(), value.strip()
    if ":" not in auth:
        die(f"{CONF_FILE}: auth must be '<user>:<password>' or "
            "'Authorization: Basic <base64>'")
    return "Authorization", "Basic " + base64.b64encode(auth.encode("utf-8")).decode("ascii")


def fetch_cert_sha256(host: str, port: int) -> str:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    conn = http.client.HTTPSConnection(host, port, timeout=10, context=ctx)
    try:
        conn.connect()
        der = conn.sock.getpeercert(binary_form=True)
    finally:
        conn.close()
    return hashlib.sha256(der).hexdigest()


def parse_duration(text: str) -> timedelta:
    m = DURATION_RE.match(text)
    if not m:
        die(f"bad duration '{text}' (expected e.g. 30m, 6h, 7d, 2w)")
    return timedelta(seconds=int(m.group(1)) * DURATION_SECS[m.group(2)])


def parse_time(text: str) -> datetime:
    """Accept ISO-8601 ('2026-08-16', '2026-08-16T07:30', with or without zone)."""
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        die(f"bad timestamp '{text}' (expected ISO-8601, e.g. 2026-08-16T07:30)")
    return dt if dt.tzinfo else dt.astimezone()


def resolve_window(args) -> tuple:
    """Return (start_dt, end_dt) from --since / --from / --to."""
    if args.since and args.since_from:
        die("use either --since or --from, not both")
    end = parse_time(args.to) if args.to else datetime.now().astimezone()
    if args.since_from:
        start = parse_time(args.since_from)
    else:
        # --since stays None unless the user passed it, so --from alone works;
        # the per-verb default is only applied here.
        start = end - parse_duration(args.since or args.default_since)
    if start >= end:
        die("empty time window (start is not before end)")
    # Loki's default max_query_length is 721h; retention here is 30 days.
    if end - start > timedelta(hours=721):
        die("time window longer than Loki's 721h query limit")
    return start, end


def to_ns(dt: datetime) -> str:
    return str(int(dt.timestamp() * 1_000_000_000))


def log_request(path: str, reason: str, status: int):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    line = f"{stamp}  LOKI GET {path}  http={status}  reason={reason or '-'}\n"
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line)


def loki_get(conf: dict, path: str, params: dict, reason: str) -> dict:
    """Perform the one and only kind of request this tool can make: a GET."""
    if params:
        path += "?" + urllib.parse.urlencode(params)
    hname, hvalue = auth_header(conf["auth"])

    if conf["scheme"] == "https":
        if conf["fingerprint"] == "-":
            die("no pinned certificate for an https:// endpoint\n"
                "Run: ccloki.py scan  and follow the instructions")
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE  # trust is the pinned fingerprint, checked below
        conn = http.client.HTTPSConnection(conf["host"], conf["port"], timeout=120, context=ctx)
    else:
        conn = http.client.HTTPConnection(conf["host"], conf["port"], timeout=120)

    print(f"[ccloki] GET {path}", file=sys.stderr)
    try:
        conn.connect()
        if conf["scheme"] == "https":
            actual = hashlib.sha256(conn.sock.getpeercert(binary_form=True)).hexdigest()
            if actual != conf["fingerprint"]:
                die("certificate fingerprint mismatch!\n"
                    f"  pinned: {conf['fingerprint']}\n  actual: {actual}\n"
                    "If the certificate was legitimately renewed, re-run scan and "
                    "re-pin; otherwise investigate before proceeding.")
        conn.request("GET", path, headers={hname: hvalue, "Accept": "application/json"})
        resp = conn.getresponse()
        body = resp.read().decode("utf-8", errors="replace")
    except OSError as e:
        die(f"cannot reach {conf['scheme']}://{conf['host']}:{conf['port']} - {e}")
    finally:
        conn.close()

    log_request(path, reason, resp.status)
    if resp.status == 401:
        die(f"HTTP 401 - the credential in {CONF_FILE} was rejected "
            "(is it the READ pair, not the write pair?)")
    if resp.status != 200:
        die(f"HTTP {resp.status} {resp.reason}: {body.strip()[:500]}")
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        die(f"non-JSON response from Loki: {body.strip()[:200]}")


def stream_tag(labels: dict) -> str:
    """Compact identity for a stream - host plus whatever names the source."""
    host = labels.get("host") or labels.get("instance") or "?"
    src = (labels.get("unit") or labels.get("container")
           or labels.get("filename") or labels.get("job") or "")
    return f"{host}/{src}" if src else host


def fmt_ts(ns: str, utc: bool) -> str:
    dt = datetime.fromtimestamp(int(ns) / 1_000_000_000,
                                timezone.utc if utc else None)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def human_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"


def label_set(labels: dict) -> str:
    pairs = ", ".join(f"{k}={v}" for k, v in sorted(labels.items()))
    return f"{{{pairs}}}" if pairs else "(no labels)"


def cmd_show(_args) -> int:
    """Print the configured store. Never prints the credential itself."""
    conf = load_conf()
    if conf["scheme"] == "https":
        pin = "pinned" if conf["fingerprint"] != "-" else "NOT PINNED"
    else:
        pin = "http (no TLS - credential crosses the network in cleartext)"
    kind = ("pre-encoded Authorization header"
            if conf["auth"].lower().startswith("authorization:")
            else f"basic auth, user '{conf['auth'].split(':', 1)[0]}'")
    print(f"url    {conf['scheme']}://{conf['host']}:{conf['port']}")
    print(f"auth   {kind}  (from {CONF_FILE})")
    print(f"tls    {pin}")
    print(f"log    {LOG_FILE}")
    return 0


def cmd_scan(_args) -> int:
    """Print the server certificate fingerprint so the USER can verify and pin it.

    Deliberately does NOT write loki.conf - verifying the fingerprint and
    pasting it into the file is the user's act.
    """
    conf = load_conf()
    if conf["scheme"] != "https":
        die("the configured url is http:// - nothing to pin")
    print(fetch_cert_sha256(conf["host"], conf["port"]))
    print(f"\nVerify this SHA-256 against the server's certificate first, then "
          f"add/replace this line in {CONF_FILE}:\n"
          f"  cert_sha256 = <the value above>", file=sys.stderr)
    return 0


def cmd_labels(args) -> int:
    conf = load_conf()
    start, end = resolve_window(args)
    data = loki_get(conf, ENDPOINTS["labels"],
                    {"start": to_ns(start), "end": to_ns(end)}, args.reason)
    for name in sorted(data.get("data") or []):
        print(name)
    return 0


def cmd_values(args) -> int:
    if not NAME_RE.match(args.label):
        die(f"invalid label name '{args.label}'")
    conf = load_conf()
    start, end = resolve_window(args)
    path = ENDPOINTS["values"].format(label=urllib.parse.quote(args.label, safe=""))
    data = loki_get(conf, path, {"start": to_ns(start), "end": to_ns(end)}, args.reason)
    for value in sorted(data.get("data") or []):
        print(value)
    return 0


def cmd_series(args) -> int:
    conf = load_conf()
    start, end = resolve_window(args)
    data = loki_get(conf, ENDPOINTS["series"],
                    {"match[]": args.selector, "start": to_ns(start), "end": to_ns(end)},
                    args.reason)
    rows = data.get("data") or []
    if args.json:
        print(json.dumps(rows, indent=2, sort_keys=True))
        return 0
    for labels in sorted(rows, key=stream_tag):
        print(f"{stream_tag(labels)}\t{label_set(labels)}")
    print(f"\n{len(rows)} stream(s)", file=sys.stderr)
    return 0


def cmd_stats(args) -> int:
    """Line/byte volume for a selector - run this before a wide fetch."""
    conf = load_conf()
    start, end = resolve_window(args)
    data = loki_get(conf, ENDPOINTS["stats"],
                    {"query": args.selector, "start": to_ns(start), "end": to_ns(end)},
                    args.reason)
    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
        return 0
    entries = data.get("entries", 0)
    print(f"window   {start:%Y-%m-%d %H:%M} .. {end:%Y-%m-%d %H:%M}")
    print(f"streams  {data.get('streams', 0)}")
    print(f"chunks   {data.get('chunks', 0)}")
    print(f"entries  {entries}")
    print(f"bytes    {human_bytes(data.get('bytes', 0))}")
    if entries > MAX_LIMIT:
        print(f"\nNote: {entries} entries exceeds the {MAX_LIMIT}-line query cap - "
              "narrow the selector, shorten the window, or add a line filter "
              "before fetching.", file=sys.stderr)
    return 0


def cmd_logs(args) -> int:
    if not 1 <= args.limit <= MAX_LIMIT:
        die(f"--limit must be between 1 and {MAX_LIMIT} (Loki's per-query cap)")
    conf = load_conf()
    start, end = resolve_window(args)
    data = loki_get(conf, ENDPOINTS["range"], {
        "query": args.query,
        "start": to_ns(start),
        "end": to_ns(end),
        "limit": str(args.limit),
        # backward = newest first, so a truncated result keeps the most recent
        # lines; they are re-sorted ascending for display below.
        "direction": args.direction,
    }, args.reason)

    if args.json:
        print(json.dumps(data.get("data"), indent=2, sort_keys=True))
        return 0

    result = (data.get("data") or {}).get("result") or []
    rtype = (data.get("data") or {}).get("resultType")
    if rtype != "streams":
        die(f"query returned '{rtype}', not log lines - use the 'query' verb "
            "for metric expressions")

    entries = []
    for stream in result:
        tag = stream_tag(stream.get("stream") or {})
        for ts, line in stream.get("values") or []:
            entries.append((int(ts), tag, line))
    entries.sort()

    width = max((len(t) for _, t, _ in entries), default=0)
    for ts, tag, line in entries:
        if args.raw:
            print(line)
        else:
            text = line.replace("\n", "\\n").replace("\r", "")
            print(f"{fmt_ts(str(ts), args.utc)}  {tag.ljust(width)}  {text}")

    print(f"\n{len(entries)} line(s) from {len(result)} stream(s), "
          f"{start:%Y-%m-%d %H:%M} .. {end:%Y-%m-%d %H:%M}", file=sys.stderr)
    if len(entries) >= args.limit:
        print(f"TRUNCATED at --limit {args.limit} "
              f"({'newest' if args.direction == 'backward' else 'oldest'} kept) - "
              "there are more matching lines. Narrow the window or add a filter.",
              file=sys.stderr)
    return 0


def cmd_query(args) -> int:
    """Metric queries (rate/count_over_time/sum by ...) - instant, or range with --step."""
    conf = load_conf()
    start, end = resolve_window(args)
    if args.step:
        parse_duration(args.step)  # validate
        data = loki_get(conf, ENDPOINTS["range"],
                        {"query": args.query, "start": to_ns(start),
                         "end": to_ns(end), "step": args.step}, args.reason)
    else:
        data = loki_get(conf, ENDPOINTS["instant"],
                        {"query": args.query, "time": to_ns(end)}, args.reason)

    payload = data.get("data") or {}
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    rtype, result = payload.get("resultType"), payload.get("result") or []
    if rtype == "vector":
        for item in sorted(result, key=lambda i: stream_tag(i.get("metric") or {})):
            print(f"{item.get('value', ['', ''])[1]}\t{label_set(item.get('metric') or {})}")
    elif rtype == "matrix":
        for item in sorted(result, key=lambda i: stream_tag(i.get("metric") or {})):
            print(label_set(item.get("metric") or {}))
            for secs, value in item.get("values") or []:
                stamp = datetime.fromtimestamp(float(secs),
                                               timezone.utc if args.utc else None)
                print(f"  {stamp:%Y-%m-%d %H:%M:%S}  {value}")
    elif rtype == "streams":
        die("that expression returns log lines - use the 'logs' verb")
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    if not result:
        print("(empty result)", file=sys.stderr)
    return 0


def add_window_args(p, default_since):
    p.add_argument("--since", metavar="DUR",
                   help=f"look back this far, e.g. 30m/6h/7d (default {default_since})")
    p.add_argument("--from", dest="since_from", metavar="TS",
                   help="window start, ISO-8601 (alternative to --since)")
    p.add_argument("--to", metavar="TS", help="window end, ISO-8601 (default: now)")
    p.add_argument("--utc", action="store_true", help="show timestamps in UTC")
    p.set_defaults(default_since=default_since)


def add_common(p):
    p.add_argument("-m", "--reason", default="",
                   help="why this query is being run (logged)")
    p.add_argument("--json", action="store_true", help="print the raw JSON result")


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="ccloki.py",
        description="Restricted read-only Loki query wrapper for Claude Code "
                    "diagnostics (GET-only, query endpoints only).",
        epilog="Quote LogQL in single quotes: '{host=\"db-server\"} |= \"error\"'")
    sub = parser.add_subparsers(dest="verb", required=True)

    sub.add_parser("show", help="show the configured store (no secrets)"
                   ).set_defaults(func=cmd_show)

    sub.add_parser("scan", help="fetch cert fingerprint for manual pinning (https only)"
                   ).set_defaults(func=cmd_scan)

    p_labels = sub.add_parser("labels", help="list label names present in the window")
    add_common(p_labels)
    add_window_args(p_labels, "24h")
    p_labels.set_defaults(func=cmd_labels)

    p_values = sub.add_parser("values", help="list the values of one label")
    add_common(p_values)
    p_values.add_argument("label", help="label name, e.g. host / unit / container")
    add_window_args(p_values, "24h")
    p_values.set_defaults(func=cmd_values)

    p_series = sub.add_parser("series", help="list streams matching a selector")
    add_common(p_series)
    p_series.add_argument("selector", help="label selector, e.g. '{host=\"db-server\"}'")
    add_window_args(p_series, "24h")
    p_series.set_defaults(func=cmd_series)

    p_stats = sub.add_parser("stats", help="line/byte volume for a selector (size a fetch first)")
    add_common(p_stats)
    p_stats.add_argument("selector", help="label selector, e.g. '{host=\"db-server\"}'")
    add_window_args(p_stats, "24h")
    p_stats.set_defaults(func=cmd_stats)

    p_logs = sub.add_parser("logs", help="fetch log lines")
    add_common(p_logs)
    p_logs.add_argument("query", help="LogQL log query, e.g. '{unit=\"cron.service\"} |= \"fail\"'")
    add_window_args(p_logs, "1h")
    p_logs.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                        help=f"max lines (default {DEFAULT_LIMIT}, cap {MAX_LIMIT})")
    p_logs.add_argument("--direction", choices=("backward", "forward"), default="backward",
                        help="which end of the window to keep when truncating "
                             "(backward = newest, default)")
    p_logs.add_argument("--raw", action="store_true",
                        help="print log lines only, no timestamp/stream columns")
    p_logs.set_defaults(func=cmd_logs)

    p_query = sub.add_parser("query", help="metric query (rate/count_over_time/sum by ...)")
    add_common(p_query)
    p_query.add_argument("query", help="LogQL metric expression")
    add_window_args(p_query, "1h")
    p_query.add_argument("--step", metavar="DUR",
                         help="evaluate over the window at this step (range query) "
                              "instead of a single instant")
    p_query.set_defaults(func=cmd_query)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
