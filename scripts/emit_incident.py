#!/usr/bin/env python3
"""Emit the evidence bundle for an operational incident fixture.

Reads ``shared/fixtures/incidents/<INCIDENT_ID>/incident.json`` plus the structured log
files it references, validates them, and prints either a human-readable summary or the raw
payload. The script is standalone: it does not import the application and it performs no
network I/O unless ``--webhook-url`` is given explicitly.

Usage:
    python3 scripts/emit_incident.py                           # INC-2026-0318-004, pretty summary
    python3 scripts/emit_incident.py INC-2026-0318-004 --format json
    python3 scripts/emit_incident.py --list
    python3 scripts/emit_incident.py --webhook-url http://localhost:9000/hooks/incidents --yes

Exit codes:
    0  success
    2  usage error or incident not found
    3  payload or evidence failed validation
    4  webhook delivery declined (no confirmation) or refused (unsupported URL)
    5  webhook delivery failed
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURES_DIR = REPO_ROOT / "shared" / "fixtures" / "incidents"
DEFAULT_INCIDENT_ID = "INC-2026-0318-004"

REQUIRED_PAYLOAD_KEYS = (
    "incident_id",
    "opened_at",
    "severity",
    "status",
    "service",
    "title",
    "affected_batch",
    "affected_payments",
    "correlation_id",
    "symptoms",
    "evidence",
    "runbook",
)
REQUIRED_LOG_FIELDS = ("timestamp", "level", "event", "logger", "service", "correlation_id")

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_INVALID = 3
EXIT_DECLINED = 4
EXIT_DELIVERY_FAILED = 5


class FixtureError(Exception):
    """Raised when the incident payload or its evidence is malformed."""


# ---------------------------------------------------------------------------
# Loading and validation
# ---------------------------------------------------------------------------


def list_incidents(fixtures_dir: Path) -> list[str]:
    if not fixtures_dir.is_dir():
        return []
    return sorted(
        p.name for p in fixtures_dir.iterdir() if p.is_dir() and (p / "incident.json").is_file()
    )


def load_payload(incident_dir: Path) -> dict[str, Any]:
    path = incident_dir / "incident.json"
    try:
        with path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except json.JSONDecodeError as exc:
        raise FixtureError(f"{path}: invalid JSON ({exc})") from exc
    if not isinstance(payload, dict):
        raise FixtureError(f"{path}: top-level value must be an object")
    missing = [key for key in REQUIRED_PAYLOAD_KEYS if key not in payload]
    if missing:
        raise FixtureError(f"{path}: missing required keys: {', '.join(missing)}")
    if payload["incident_id"] != incident_dir.name:
        raise FixtureError(
            f"{path}: incident_id {payload['incident_id']!r} does not match "
            f"directory {incident_dir.name!r}"
        )
    evidence = payload["evidence"]
    if not isinstance(evidence, dict) or not isinstance(evidence.get("logs"), list):
        raise FixtureError(f"{path}: evidence.logs must be a list of file names")
    return payload


def summarise_log(path: Path) -> dict[str, Any]:
    """Return line counts, level counts, time span and notable (warning/error) lines."""
    if not path.is_file():
        raise FixtureError(f"evidence log not found: {path}")
    levels: Counter = Counter()
    events: Counter = Counter()
    notable: list[dict[str, Any]] = []
    first_ts: str | None = None
    last_ts: str | None = None
    count = 0
    with path.open("r", encoding="utf-8") as fh:
        for number, raw in enumerate(fh, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                record = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise FixtureError(f"{path}:{number}: invalid JSON ({exc})") from exc
            missing = [f for f in REQUIRED_LOG_FIELDS if f not in record]
            if missing:
                raise FixtureError(f"{path}:{number}: missing log fields {', '.join(missing)}")
            count += 1
            levels[str(record["level"])] += 1
            events[str(record["event"])] += 1
            ts = str(record["timestamp"])
            if first_ts is None:
                first_ts = ts
            if last_ts is not None and ts < last_ts:
                raise FixtureError(
                    f"{path}:{number}: timestamps are not monotonic ({ts} < {last_ts})"
                )
            last_ts = ts
            if str(record["level"]).lower() in ("warning", "warn", "error", "critical"):
                notable.append(
                    {
                        "line": number,
                        "timestamp": ts,
                        "level": record["level"],
                        "event": record["event"],
                        "entry_ref": record.get("entry_ref"),
                        "payment_ref": record.get("payment_ref"),
                        "journal_ref": record.get("journal_ref"),
                        "detail": record.get("error")
                        or record.get("variance")
                        or record.get("to_status"),
                    }
                )
    if count == 0:
        raise FixtureError(f"{path}: no log lines")
    return {
        "file": path.name,
        "path": str(path),
        "lines": count,
        "levels": dict(sorted(levels.items())),
        "distinct_events": len(events),
        "first_timestamp": first_ts,
        "last_timestamp": last_ts,
        "notable": notable,
    }


def build_bundle(fixtures_dir: Path, incident_id: str) -> dict[str, Any]:
    incident_dir = fixtures_dir / incident_id
    if not incident_dir.is_dir():
        available = ", ".join(list_incidents(fixtures_dir)) or "none"
        raise FileNotFoundError(
            f"incident {incident_id!r} not found under {fixtures_dir} (available: {available})"
        )
    payload = load_payload(incident_dir)
    logs = [summarise_log(incident_dir / name) for name in payload["evidence"]["logs"]]
    repo_paths = [
        {"path": p, "exists": (REPO_ROOT / p).exists()}
        for p in payload["evidence"].get("repo_paths", [])
    ]
    runbook = payload["runbook"]
    return {
        "incident_dir": str(incident_dir),
        "payload": payload,
        "logs": logs,
        "repo_paths": repo_paths,
        "runbook": {"path": runbook, "exists": (REPO_ROOT / runbook).is_file()},
        "readme": {
            "path": str(incident_dir / "README.md"),
            "exists": (incident_dir / "README.md").is_file(),
        },
    }


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render_pretty(bundle: dict[str, Any]) -> str:
    p = bundle["payload"]
    out: list[str] = []
    out.append(f"{p['incident_id']}  {p['severity']}  {p['status']}  {p['service']}")
    out.append(p["title"])
    out.append("")
    out.append(f"  opened_at         {p['opened_at']}")
    if p.get("opened_by"):
        out.append(f"  opened_by         {p['opened_by']}")
    if p.get("updated_at"):
        out.append(f"  updated_at        {p['updated_at']} ({p.get('updated_by', 'unknown')})")
    out.append(f"  correlation_id    {p['correlation_id']}")
    out.append(f"  affected_batch    {p['affected_batch']}")
    out.append(f"  affected_payments {', '.join(p['affected_payments'])}")
    recon = p.get("reconciliation")
    if isinstance(recon, dict):
        out.append(
            "  reconciliation    "
            f"{recon.get('run_ref', '?')} {recon.get('status', '?')}: "
            f"expected {recon.get('expected_total')} "
            f"recorded {recon.get('recorded_total')} "
            f"variance {recon.get('variance')} {recon.get('currency', '')}"
        )
        if recon.get("unmatched_refs"):
            out.append(f"  unmatched_refs    {', '.join(recon['unmatched_refs'])}")
    out.append("")
    out.append("Symptoms")
    for index, symptom in enumerate(p["symptoms"], 1):
        out.append(f"  {index}. {symptom}")
    out.append("")
    out.append("Evidence logs")
    for log in bundle["logs"]:
        levels = ", ".join(f"{k} {v}" for k, v in log["levels"].items())
        out.append(
            f"  {log['file']:<26} {log['lines']:>3} lines  ({levels})  "
            f"{log['first_timestamp']} -> {log['last_timestamp']}"
        )
        for item in log["notable"]:
            refs = " ".join(
                str(item[k]) for k in ("entry_ref", "payment_ref", "journal_ref") if item.get(k)
            )
            detail = f"  {item['detail']}" if item.get("detail") else ""
            out.append(
                f"      L{item['line']:<3} {item['timestamp']}  {item['level']:<7} "
                f"{item['event']}  {refs}{detail}"
            )
    out.append("")
    out.append("Repository paths")
    for item in bundle["repo_paths"]:
        marker = "present" if item["exists"] else "missing"
        out.append(f"  {item['path']:<64} {marker}")
    out.append("")
    out.append("Paths")
    out.append(f"  evidence  {bundle['incident_dir']}")
    readme_state = "present" if bundle["readme"]["exists"] else "missing"
    runbook_state = "present" if bundle["runbook"]["exists"] else "missing"
    out.append(f"  readme    {bundle['readme']['path']}  ({readme_state})")
    out.append(f"  runbook   {bundle['runbook']['path']}  ({runbook_state})")
    automation = p.get("automation")
    if isinstance(automation, dict) and automation.get("suggested_instruction_ref"):
        out.append(f"  automation {automation['suggested_instruction_ref']}")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Optional webhook delivery (opt-in)
# ---------------------------------------------------------------------------


def confirm(prompt: str) -> bool:
    if not sys.stdin.isatty():
        return False
    try:
        answer = input(prompt)
    except EOFError:
        return False
    return answer.strip().lower() in ("y", "yes")


def post_webhook(url: str, payload: dict[str, Any], timeout: float) -> int:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        print(f"error: --webhook-url must be an http(s) URL (got {url!r})", file=sys.stderr)
        return EXIT_DECLINED
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "User-Agent": "meridian-flow-emit-incident/1.0",
            "X-Correlation-ID": str(payload.get("correlation_id", "")),
            "X-Incident-ID": str(payload.get("incident_id", "")),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            snippet = response.read(512).decode("utf-8", errors="replace").strip()
    except urllib.error.HTTPError as exc:
        print(f"webhook delivery failed: HTTP {exc.code} from {url}", file=sys.stderr)
        return EXIT_DELIVERY_FAILED
    except (urllib.error.URLError, OSError) as exc:
        print(f"webhook delivery failed: {exc}", file=sys.stderr)
        return EXIT_DELIVERY_FAILED
    print(f"webhook delivered: HTTP {status} from {url}")
    if snippet:
        print(f"  response: {snippet}")
    return EXIT_OK


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="emit_incident.py",
        description=(
            "Print (and optionally deliver) an incident evidence bundle "
            "from shared/fixtures/incidents."
        ),
        epilog="No network I/O happens unless --webhook-url is given.",
    )
    parser.add_argument(
        "incident_id",
        nargs="?",
        default=DEFAULT_INCIDENT_ID,
        help=f"incident reference (default: {DEFAULT_INCIDENT_ID})",
    )
    parser.add_argument(
        "--format",
        choices=("pretty", "json"),
        default="pretty",
        help="pretty summary (default) or the raw incident.json payload",
    )
    parser.add_argument(
        "--fixtures-dir",
        default=str(DEFAULT_FIXTURES_DIR),
        help="directory containing one folder per incident",
    )
    parser.add_argument("--list", action="store_true", help="list available incident ids and exit")
    parser.add_argument(
        "--webhook-url",
        metavar="URL",
        help="OPT-IN: POST the payload as JSON to this http(s) URL after confirmation",
    )
    parser.add_argument(
        "--yes", action="store_true", help="skip the confirmation prompt for --webhook-url"
    )
    parser.add_argument(
        "--timeout", type=float, default=10.0, help="webhook timeout in seconds (default 10)"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    fixtures_dir = Path(args.fixtures_dir).resolve()

    if args.list:
        ids = list_incidents(fixtures_dir)
        if not ids:
            print(f"no incidents found under {fixtures_dir}")
            return EXIT_USAGE
        for incident_id in ids:
            print(incident_id)
        return EXIT_OK

    try:
        bundle = build_bundle(fixtures_dir, args.incident_id)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except FixtureError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_INVALID

    if args.format == "json":
        print(json.dumps(bundle["payload"], indent=2, ensure_ascii=False))
    else:
        print(render_pretty(bundle))

    if not args.webhook_url:
        return EXIT_OK

    payload = bundle["payload"]
    if not args.yes:
        size = len(json.dumps(payload))
        prompt = f"\nPOST {payload['incident_id']} ({size} bytes) to {args.webhook_url}? [y/N] "
        if not confirm(prompt):
            print("webhook delivery declined (pass --yes to skip the prompt)", file=sys.stderr)
            return EXIT_DECLINED
    return post_webhook(args.webhook_url, payload, args.timeout)


if __name__ == "__main__":
    sys.exit(main())
