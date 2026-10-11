"""Exact reuse eligibility; no network, record contents or publication."""
import copy
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "skills/record-backup/scripts/check_manual_verification.py"
spec = importlib.util.spec_from_file_location("manual", path)
manual = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manual)


class ManualVerificationTests(unittest.TestCase):
    def setUp(self):
        self.record = dict(source_provider="fixture", source_container="root", source_id="file-1",
                           repository_path="records/file.pdf", byte_size=3, sha256="a" * 64)
        self.destination = dict(repository="fixture/backup", branch="main")
        self.entry = self.record | dict(id="check-1", destination=self.destination.copy(),
            remote_blob_id="b" * 40, verified_on="2026-10-11", verified_by="user",
            evidence_reference="explicit manual check and reuse authorization",
            basis="user-reported-github-raw-download", revoked=False,
            reuse_policy="until-identity-version-or-content-changes")

    def check(self, entry=None, record=None, destination=None, blob=None, at="2026-10-18"):
        return manual.eligible(self.entry if entry is None else entry,
            self.record if record is None else record, self.destination if destination is None else destination,
            "b" * 40 if blob is None else blob, at)

    def test_unchanged_content_reuses_check_without_mutation(self):
        before = copy.deepcopy(self.entry)
        self.assertTrue(self.check())
        self.assertEqual(before, self.entry)

    def test_each_scope_change_invalidates_reuse(self):
        for field in self.record:
            with self.subTest(field=field):
                self.assertFalse(self.check(record=self.record | {field: 4 if field == "byte_size" else "changed"}))
        self.assertFalse(self.check(record=self.record | {"source_version": 2}))
        self.assertFalse(self.check(destination=self.destination | {"branch": "other"}))
        self.assertFalse(self.check(destination=self.destination | {"repository": "other/backup"}))
        self.assertFalse(self.check(blob="c" * 40))

    def test_versions_must_match_when_exposed(self):
        entry = self.entry | {"source_version": 2}
        self.assertTrue(self.check(entry=entry, record=self.record | {"source_version": 2}))
        self.assertFalse(self.check(entry=entry, record=self.record | {"source_version": 3}))
        self.assertFalse(self.check(entry=self.entry | {"source_version": 1}, record=self.record | {"source_version": True}))
        self.assertFalse(self.check(entry=entry))

    def test_invalid_or_unauthorized_evidence_fails(self):
        for change in ({"revoked": True}, {"revoked": None}, {"basis": "source-download"},
                       {"reuse_policy": "once"}, {"evidence_reference": ""}, {"verified_on": "unknown"},
                       {"byte_size": True}, {"sha256": "invalid"}, {"remote_blob_id": "invalid"}):
            with self.subTest(change=change):
                self.assertFalse(self.check(entry=self.entry | change))
        self.assertFalse(self.check(at="2026-10-10"))
        self.assertFalse(self.check(at=None))

    def test_policy_success_does_not_override_failed_fresh_restore(self):
        reporting_spec = importlib.util.spec_from_file_location("reporting", path.with_name("reporting.py"))
        reporting = importlib.util.module_from_spec(reporting_spec)
        reporting_spec.loader.exec_module(reporting)
        value = dict(schema_version=1, run_id="weekly-1", mode="weekly", status="verified-no-change",
            started_at="2026-10-18T01:00:00Z", ended_at="2026-10-18T01:01:00Z", snapshot_commit="a" * 40,
            checks=dict(local_snapshot=True, remote_snapshot=True, manual_verification_reuse=True,
                        recovery_policy_satisfied=True), scope="fixture", exclusions="fixture", history_coverage="observed",
            coverage_limits=["unchanged file uses authorized manual check"], current_state_complete=True,
            counts=dict(records=1, bytes=3, changed=0, deleted=0),
            discovery=dict(listing_calls=1, content_reads=1, duplicates=0, pointer_cycles=0, retries=0),
            repaired_items=[], unrecoverable_gaps=[], source_access_limits=[],
            restore_test="policy satisfied; fresh full remote restore not claimed",
            reused_manual_verifications=[dict(id="check-1", snapshot_commit="a" * 40, verified_on="2026-10-11")])
        reporting.validate_receipt(value, "weekly-1")
        for key in ("full_latest_restore", "full_older_restore"):
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError, "failed recovery drill"):
                    reporting.validate_receipt(value | {"checks": value["checks"] | {key: False}}, "weekly-1")


if __name__ == "__main__":
    unittest.main()
