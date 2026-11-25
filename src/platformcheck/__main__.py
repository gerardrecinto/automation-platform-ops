import argparse
import json
import pathlib
import sys

from .baseline import check, summarize
from .evidence import collect


def main() -> int:
    p = argparse.ArgumentParser(prog="platformcheck")
    sub = p.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("harden", help="check a compose file against the baseline")
    h.add_argument("compose")
    e = sub.add_parser("evidence", help="print audit evidence as JSON")
    e.add_argument("--backups", default="backups")
    e.add_argument("--compose", default="compose.yaml")
    e.add_argument("--max-backup-age-hours", type=float, default=26)
    a = p.parse_args()

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
    unproven = not (ev["restore_test"] or {}).get("passed")
    if stale:
        print("evidence: backup missing or older than the limit", file=sys.stderr)
    if unproven:
        print("evidence: no passing restore test on record", file=sys.stderr)
    return 1 if stale or unproven or ev["baseline"]["failed"] else 0


sys.exit(main())
