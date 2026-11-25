"""Audit evidence from files and the Docker daemon: what is running, when it was last backed up, whether a restore was proven."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
import subprocess

from .baseline import check, summarize

FMT = "%Y%m%dT%H%M%SZ"


def _age_hours(stamp: str, now: dt.datetime) -> float:
    return round((now - dt.datetime.strptime(stamp, FMT).replace(tzinfo=dt.timezone.utc)).total_seconds() / 3600, 2)


def _secret_ages(backups: pathlib.Path, now: dt.datetime) -> dict:
    path = backups / "rotations.json"
    ledger = json.loads(path.read_text()) if path.exists() else []
    latest: dict = {}
    for row in ledger:
        latest[row["secret"]] = row["at"]
    return {k: {"last_set": v, "age_days": round(_age_hours(v, now) / 24, 1)} for k, v in latest.items()}


def collect(backups: pathlib.Path, compose: pathlib.Path, now: dt.datetime | None = None, images: dict | None = None) -> dict:
    now = now or dt.datetime.now(dt.timezone.utc)
    manifest = json.loads((backups / "manifest.json").read_text()) if (backups / "manifest.json").exists() else []
    restore = json.loads((backups / "restore-test.json").read_text()) if (backups / "restore-test.json").exists() else None
    findings = check(compose.read_text())
    passed, failed = summarize(findings)
    latest = manifest[-1] if manifest else None
    return {
        "generated_at": now.strftime(FMT),
        "compose_sha256": hashlib.sha256(compose.read_bytes()).hexdigest(),
        "images": images if images is not None else running_images(),
        "backup": {
            "count": len(manifest),
            "latest": latest["file"] if latest else None,
            "latest_age_hours": _age_hours(latest["taken_at"], now) if latest else None,
            "latest_sha256": latest["sha256"] if latest else None,
        },
        "restore_test": restore,
        "secrets": _secret_ages(backups, now),
        "baseline": {"passed": passed, "failed": failed, "failures": [f for f in findings if not f["passed"]]},
        "control_notes": [
            "Backup age and restore proof are evidence for a recovery control.",
            "Baseline rule ids B1 to B8 are cited in the findings.",
            "Secret age comes from the rotation ledger written by scripts/up.sh and scripts/rotate-db-password.sh.",
            "Access reviews are a process control; this tool does not evidence them.",
        ],
    }


def running_images() -> dict:
    try:
        out = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"], capture_output=True, text=True, check=True
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return {}
    rows = [json.loads(line) for line in out.splitlines() if line.strip()]
    return {r["Service"]: r["Image"] for r in rows}
