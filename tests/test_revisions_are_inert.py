"""After consolidation the revision machinery answers nothing.

Adversarial review F1/F23/F24. Revisions were retired by ruling on
2026-08-16 and the migration runs at boot (`_collapse_legacy_revisions`),
but 457 lines of `revisions.py`, seven routes and eleven `assemble.py` call
sites still stand over data that no longer has revisions in it — two live
answers to "what was this panel approved as?", the other being the approval
snapshot the codebase itself calls the better one.

This file is the PRECONDITION for deleting them: it pins that on
consolidated data the machinery is provably inert, so the deletion is a
simplification rather than a behaviour change. It is deliberately written
against the reduction rather than the implementation — if
`qualifying_approved_by_panel` ever stops equalling "newest approved take
per panel", the deletion is not safe and this fails first.

It also pins the one state where that is NOT true: a chain that failed to
consolidate. No such chain has ever been recorded, and F23 made the
failure visible, but the guard belongs here rather than in a comment."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class OnConsolidatedDataTheMachineryIsInert(unittest.TestCase):
    def setUp(self):
        from app import paths
        self.tmp = tempfile.TemporaryDirectory()
        home = Path(self.tmp.name)
        self._old = {k: getattr(paths, k) for k in
                     ("SPECS_DIR", "SPEC_LOCKS", "BOARDS_DIR", "APPROVAL_LOG")}
        for sub in ("specs", "boards", "state"):
            (home / sub).mkdir(parents=True)
        paths.SPECS_DIR = home / "specs"
        paths.SPEC_LOCKS = home / "specs" / "locks.json"
        paths.BOARDS_DIR = home / "boards"
        paths.APPROVAL_LOG = home / "state" / "approval_log.md"

        spec = {"specification_id": "BOARD_A", "subject": "s",
                "mode": "CANON_EXTRACTION", "board_type": "SCENE",
                "panels": [{"id": "P01", "title": "a", "purpose": "p",
                            "required_objects": []},
                           {"id": "P02", "title": "b", "purpose": "p",
                            "required_objects": []}],
                "evidence_ledger": []}
        (paths.SPECS_DIR / "BOARD_A.json").write_text(json.dumps(spec),
                                                      encoding="utf-8")
        (paths.SPEC_LOCKS).write_text(json.dumps(
            {"BOARD_A": {"hash": "h" * 64, "approved_at": "2026-01-01T00:00:00+00:00"}}),
            encoding="utf-8")
        d = paths.BOARDS_DIR / "BOARD_A"
        d.mkdir(parents=True)
        for cid, pid, status in (("CAND-001", "P01", "REJECTED"),
                                 ("CAND-002", "P02", "APPROVED"),
                                 ("CAND-004", "P01", "APPROVED"),
                                 ("CAND-003", "P01", "APPROVED")):
            (d / f"{cid}.json").write_text(json.dumps({
                "candidate_id": cid, "panel_id": pid, "status": status,
                "specification_id": "BOARD_A", "width": 100, "height": 100,
            }), encoding="utf-8")

    def tearDown(self):
        from app import paths
        for k, v in self._old.items():
            setattr(paths, k, v)
        self.tmp.cleanup()

    def test_there_is_only_one_revision(self):
        from app import revisions
        self.assertEqual(revisions.revisions_of("BOARD_A"), ["BOARD_A"])
        self.assertEqual(revisions.base_of("BOARD_A"), "BOARD_A")
        self.assertEqual(revisions.revision_of("BOARD_A"), 1)

    def test_every_panel_floor_is_one(self):
        from app import revisions
        for pid in ("P01", "P02"):
            self.assertEqual(revisions.panel_revision_floor("BOARD_A", pid), 1)

    def test_nothing_is_offered_below_the_floor(self):
        """`offered` is what SLOT_OFFERED and the Keep verb render from
        (F24). Empty means both are dead branches."""
        from app import revisions
        q = revisions.qualifying_approved_by_panel("BOARD_A")
        self.assertEqual(q["offered"], {})

    def test_the_keeps_registry_is_empty(self):
        from app import revisions
        self.assertEqual(revisions.load_keeps("BOARD_A"), {})

    def test_qualifying_reduces_to_newest_approved_per_panel(self):
        """THE reduction. If this ever fails, deleting revisions.py would
        change which takes a board uses, and the deletion is not safe."""
        from app import generate, revisions
        q = revisions.qualifying_approved_by_panel("BOARD_A")["qualifying"]
        got = {pid: rec["candidate_id"] for pid, rec in q.items()}

        def cand_num(cid):
            return int(str(cid).rsplit("-", 1)[-1])

        naive = {}
        for c in generate.list_candidates("BOARD_A"):
            if c.get("status") != "APPROVED":
                continue
            if not str(c.get("candidate_id", "")).startswith("CAND-"):
                continue
            pid = c["panel_id"]
            if pid not in naive or cand_num(c["candidate_id"]) > cand_num(naive[pid]):
                naive[pid] = c["candidate_id"]

        self.assertEqual(got, naive)
        self.assertEqual(got, {"P01": "CAND-004", "P02": "CAND-002"},
                         "newest approved id wins, rejected ignored")


class ASkippedChainIsTheOneUnsafeState(unittest.TestCase):
    """The precondition on the precondition. A chain that did not collapse
    is where the naive read would differ — and it used to be invisible."""

    def test_skips_are_reachable_not_just_logged(self):
        from app import revisions
        self.assertTrue(hasattr(revisions, "skipped_migrations"))
        self.assertIsInstance(revisions.skipped_migrations(), list)

    def test_a_skip_reaches_the_blocker_list(self):
        from app import insights, revisions
        revisions._SKIPPED.append(
            {"project": "p", "base": "BOARD_X", "reason": "take id collision"})
        try:
            rows = [r for r in insights.blocking()
                    if "BOARD_X" in str(r.get("text", ""))]
        finally:
            revisions._SKIPPED.clear()
        self.assertEqual(len(rows), 1)
        self.assertIn("did not consolidate", rows[0]["text"])
        self.assertIn("take id collision", rows[0]["text"])

    def test_the_boot_states_skips_as_loudly_as_successes(self):
        main = (ROOT / "app/main.py").read_text(encoding="utf-8")
        i = main.index("def _collapse_legacy_revisions")
        seg = main[i:i + 1400]
        self.assertIn("for r in revisions.skipped_migrations():", seg)
        self.assertIn("SKIPPED", seg)


if __name__ == "__main__":
    unittest.main()
