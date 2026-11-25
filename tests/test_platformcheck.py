import datetime as dt
import json
import pathlib

from platformcheck.baseline import check, summarize
from platformcheck.evidence import collect

ROOT = pathlib.Path(__file__).resolve().parent.parent
GOOD = (ROOT / "compose.yaml").read_text()


def failed(text):
    return {(f["service"], f["rule"].split()[0]) for f in check(text) if not f["passed"]}


def test_shipped_compose_file_passes_every_rule():
    assert summarize(check(GOOD)) [1] == 0


def test_latest_tag_fails_b1():
    assert ("redis", "B1") in failed(GOOD.replace("redis:7.4.1", "redis:latest"))


def test_unpinned_default_fails_b1():
    assert ("n8n", "B1") in failed(GOOD.replace("${N8N_VERSION:-1.78.1}", "${N8N_VERSION:-latest}"))


def test_public_port_fails_b2():
    assert ("n8n", "B2") in failed(GOOD.replace('"127.0.0.1:5678:5678"', '"5678:5678"'))


def test_literal_password_fails_b3():
    assert ("postgres", "B3") in failed(GOOD.replace("POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?run scripts/up.sh}", "POSTGRES_PASSWORD: hunter2", 1))


def test_redis_eviction_policy_fails_b7():
    assert ("redis", "B7") in failed(GOOD.replace("noeviction", "allkeys-lru"))


def test_evidence_reports_backup_age_and_restore(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps([{"file": "b.dump", "taken_at": "20261124T010000Z", "sha256": "ab", "bytes": 1}]))
    (tmp_path / "restore-test.json").write_text(json.dumps({"passed": True}))
    now = dt.datetime(2026, 11, 24, 7, 0, tzinfo=dt.timezone.utc)
    ev = collect(tmp_path, ROOT / "compose.yaml", now=now, images={"n8n": "x"})
    assert ev["backup"]["latest_age_hours"] == 6.0
    assert ev["restore_test"]["passed"] is True and ev["baseline"]["failed"] == 0


def test_evidence_with_no_backups_has_no_age(tmp_path):
    ev = collect(tmp_path, ROOT / "compose.yaml", images={})
    assert ev["backup"]["latest_age_hours"] is None and ev["restore_test"] is None
