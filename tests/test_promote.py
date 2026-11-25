import datetime as dt
import json
import pathlib

from platformcheck.evidence import collect
from platformcheck.promote import gate, record

ROOT = pathlib.Path(__file__).resolve().parent.parent
NOW = dt.datetime(2026, 11, 24, 7, 0, tzinfo=dt.timezone.utc)


def evidence(tmp_path, restore=True):
    backups = tmp_path / "backups"
    backups.mkdir()
    (backups / "manifest.json").write_text(json.dumps([{"file": "b.dump", "taken_at": "20261124T010000Z", "sha256": "ab", "bytes": 1}]))
    if restore:
        (backups / "restore-test.json").write_text(json.dumps({"passed": True}))
    return collect(backups, ROOT / "compose.yaml", now=NOW, images={})


def test_dev_needs_no_earlier_record(tmp_path):
    assert gate("dev", "1.80.0", evidence(tmp_path), tmp_path / "changes", None) == []


def test_qa_refused_without_a_dev_record(tmp_path):
    problems = gate("qa", "1.80.0", evidence(tmp_path), tmp_path / "changes", None)
    assert problems == ["1.80.0 has no change record in dev"]


def test_qa_allowed_after_dev_record(tmp_path):
    ev, changes = evidence(tmp_path), tmp_path / "changes"
    record("dev", "1.80.0", ev, changes, None, now=NOW)
    assert gate("qa", "1.80.0", ev, changes, None) == []


def test_record_for_another_version_does_not_count(tmp_path):
    ev, changes = evidence(tmp_path), tmp_path / "changes"
    record("dev", "1.79.0", ev, changes, None, now=NOW)
    assert gate("qa", "1.80.0", ev, changes, None)


def test_latest_is_never_promoted(tmp_path):
    assert gate("dev", "latest", evidence(tmp_path), tmp_path / "changes", None)


def test_no_restore_proof_blocks_promotion(tmp_path):
    problems = gate("dev", "1.80.0", evidence(tmp_path, restore=False), tmp_path / "changes", None)
    assert "no passing restore test on record" in problems


def test_uat_and_prod_need_an_approver(tmp_path):
    ev, changes = evidence(tmp_path), tmp_path / "changes"
    record("qa", "1.80.0", ev, changes, None, now=NOW)
    assert "uat needs --approver" in gate("uat", "1.80.0", ev, changes, None)
    assert gate("uat", "1.80.0", ev, changes, "J. Doe") == []


def test_record_keeps_evidence_and_approver(tmp_path):
    ev = evidence(tmp_path)
    body = json.loads(record("prod", "1.80.0", ev, tmp_path / "changes", "J. Doe", now=NOW).read_text())
    assert body["approved_by"] == "J. Doe" and body["evidence"]["backup_sha256"] == "ab"


def test_secret_age_comes_from_the_ledger(tmp_path):
    (tmp_path / "rotations.json").write_text(json.dumps([
        {"secret": "POSTGRES_PASSWORD", "at": "20260824T070000Z"},
        {"secret": "POSTGRES_PASSWORD", "at": "20261114T070000Z"},
    ]))
    ev = collect(tmp_path, ROOT / "compose.yaml", now=NOW, images={})
    assert ev["secrets"]["POSTGRES_PASSWORD"]["age_days"] == 10.0
