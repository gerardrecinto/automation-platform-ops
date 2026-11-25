import argparse
import json
import pathlib
import sys

from .baseline import check, summarize
from .evidence import collect
from .promote import ORDER, gate, record


def main() -> int:
    p = argparse.ArgumentParser(prog="platformcheck")
    sub = p.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("harden", help="check a compose file against the baseline")
    h.add_argument("compose")
    e = sub.add_parser("evidence", help="print audit evidence as JSON")
    e.add_argument("--backups", default="backups")
    e.add_argument("--compose", default="compose.yaml")
    e.add_argument("--max-backup-age-hours", type=float, default=26)
    e.add_argument("--max-secret-age-days", type=float, default=90)
    r = sub.add_parser("promote", help="check the gate and write a change record")
    r.add_argument("env", choices=ORDER)
    r.add_argument("--version", required=True)
    r.add_argument("--approver")
    r.add_argument("--backups", default="backups")
    r.add_argument("--compose", default="compose.yaml")
    r.add_argument("--changes", default="changes")
    r.add_argument("--dry-run", action="store_true")
    a = p.parse_args()

    if a.cmd == "promote":
        changes = pathlib.Path(a.changes)
        ev = collect(pathlib.Path(a.backups), pathlib.Path(a.compose))
        problems = gate(a.env, a.version, ev, changes, a.approver)
        for x in problems:
            print("refused: " + x, file=sys.stderr)
        if problems:
            return 1
        if a.dry_run:
            print(f"allowed: {a.version} -> {a.env}")
            return 0
        print(record(a.env, a.version, ev, changes, a.approver))
        return 0

    if a.cmd == "harden":
        findings = check(pathlib.Path(a.compose).read_text())
        for f in findings:
            print(("PASS " if f["passed"] else "FAIL ") + f"{f['service']:9} {f['rule']}")
        ok, bad = summarize(findings)
        print(f"{ok} passed, {bad} failed")
        return 1 if bad else 0

    ev = collect(pathlib.Path(a.backups), pathlib.Path(a.compose))
    print(json.dumps(ev, indent=2))
    age = ev["backup"]["latest_age_hours"]
    stale = age is None or age > a.max_backup_age_hours
    old = [k for k, v in ev["secrets"].items() if v["age_days"] > a.max_secret_age_days]
    for k in old:
        print(f"evidence: {k} is older than {a.max_secret_age_days:g} days", file=sys.stderr)
    unproven = not (ev["restore_test"] or {}).get("passed")
    if stale:
        print("evidence: backup missing or older than the limit", file=sys.stderr)
    if unproven:
        print("evidence: no passing restore test on record", file=sys.stderr)
    return 1 if stale or unproven or old or ev["baseline"]["failed"] else 0


sys.exit(main())
