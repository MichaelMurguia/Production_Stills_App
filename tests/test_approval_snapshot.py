"""One breakdown, per-panel gates — the foundation (user rulings
2026-08-16).

Revisions existed to answer "what was this approved AS?". A snapshot
answers it better: the document that produced a take is frozen onto the
take itself, so it stays true however the breakdown moves on. That is
what lets a single breakdown be edited in place without losing the thing
an approval is supposed to guarantee.

Withdrawing an approval is its own act, distinct from rejecting: a
rejection is a judgement that rides into every future prompt for the
panel, and wanting to change a brief is not that."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import generate, paths, store  # noqa: E402

SPEC = {
    "specification_id": "S1",
    "subject": "A shack",
    "mode": "CANON_EXTRACTION",
    "revision": 1,
    "scene": "A shack at dusk.",
    "render_intent": "Grounded and painterly.",
    "forbidden_elements": ["unsupported animals"],
    "design_languages": ["RESISTANCE"],
    "panels": [
        {"id": "P01", "title": "Interior", "purpose": "Show the workshop.",
         "required_objects": ["cast-iron stove", "worktable"]},
        {"id": "P02", "title": "Exterior", "purpose": "Show the meadow.",
         "required_objects": ["thin line of smoke"]},
    ],
    "evidence_ledger": [
        {"panel_id": "P01", "object": "cast-iron stove",
         "evidence_class": "SCRIPT_EXPLICIT", "source": "INT. SHACK: a stove.",
         "status": "PASS"},
        {"panel_id": "P02", "object": "thin line of smoke",
         "evidence_class": "SCRIPT_EXPLICIT", "source": "EXT: smoke curls.",
         "status": "PASS"},
    ],
}


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-snap-"))
        self._saved = (paths.HOME, paths.PROJECTS_DIR,
                       paths.ACTIVE_PROJECT_FILE, paths.SETTINGS,
                       paths.ACTIVE_PROJECT)
        paths.HOME = self.tmp
        paths.PROJECTS_DIR = self.tmp / "projects"
        paths.ACTIVE_PROJECT_FILE = self.tmp / "active_project.json"
        paths.SETTINGS = self.tmp / "settings.json"
        paths.set_project("")
        paths.ensure_dirs()
        paths.SPECS_DIR.mkdir(parents=True, exist_ok=True)
        (paths.SPECS_DIR / "S1.json").write_text(
            json.dumps(SPEC), encoding="utf-8")
        d = paths.BOARDS_DIR / "S1"
        d.mkdir(parents=True, exist_ok=True)
        (d / "CAND-0001.json").write_text(json.dumps({
            "candidate_id": "CAND-0001", "specification_id": "S1",
            "panel_id": "P01", "status": "CANDIDATE", "spec_hash": "abc123",
            "width": 3136, "height": 1344,
        }), encoding="utf-8")

    def tearDown(self):
        (paths.HOME, paths.PROJECTS_DIR, paths.ACTIVE_PROJECT_FILE,
         paths.SETTINGS, slug) = self._saved
        paths.set_project(slug)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def approve(self):
        return generate.set_candidate_status("S1", "CAND-0001", "APPROVED")

    def test_approving_freezes_the_document_that_produced_it(self):
        snap = self.approve()["approved_spec"]
        self.assertEqual(snap["panel"]["purpose"], "Show the workshop.")
        self.assertEqual(snap["board"]["scene"], "A shack at dusk.")
        self.assertEqual(snap["board"]["render_intent"], "Grounded and painterly.")
        self.assertIn("unsupported animals", snap["board"]["forbidden_elements"])
        self.assertTrue(snap["taken_at"])

    def test_the_snapshot_freezes_this_panels_evidence_only(self):
        """User ruling: the rows that justify what got rendered are part of
        what was approved. Another panel's rows are not."""
        snap = self.approve()["approved_spec"]
        objs = [r["object"] for r in snap["evidence"]]
        self.assertIn("cast-iron stove", objs)
        self.assertNotIn("thin line of smoke", objs, "P02's row is not P01's")

    def test_the_snapshot_survives_the_breakdown_moving_on(self):
        """The whole point: one breakdown, edited in place, and an approved
        take still carries what it was approved against."""
        self.approve()
        spec = store.get_spec("S1")
        spec["panels"][1]["purpose"] = "Something else entirely."
        spec["scene"] = "Rewritten scene."
        (paths.SPECS_DIR / "S1.json").write_text(json.dumps(spec), encoding="utf-8")
        rec = generate.get_candidate("S1", "CAND-0001")
        self.assertEqual(rec["approved_spec"]["board"]["scene"], "A shack at dusk.")
        self.assertEqual(rec["approved_spec"]["panel"]["purpose"],
                         "Show the workshop.")

    def test_it_is_a_copy_not_a_live_reference(self):
        snap = self.approve()["approved_spec"]
        spec = store.get_spec("S1")
        spec["panels"][0]["required_objects"].append("a new thing")
        self.assertNotIn("a new thing", snap["panel"]["required_objects"])


class UnapproveTests(SnapshotTests):
    def test_withdrawing_is_not_rejecting(self):
        self.approve()
        rec = generate.unapprove_candidate("S1", "CAND-0001")
        self.assertEqual(rec["status"], "CANDIDATE")
        self.assertNotIn("status_reason", rec,
                         "a withdrawal carries no reason into future prompts")
        self.assertTrue(rec["unapproved_at"])

    def test_the_image_and_its_history_are_untouched(self):
        self.approve()
        generate.unapprove_candidate("S1", "CAND-0001")
        rec = generate.get_candidate("S1", "CAND-0001")
        self.assertEqual(rec["spec_hash"], "abc123")
        self.assertIn("approved_spec", rec,
                      "what it was once approved against stays true")

    def test_withdrawing_what_is_not_approved_is_refused(self):
        with self.assertRaises(generate.GenerationError):
            generate.unapprove_candidate("S1", "CAND-0001")

    def test_the_withdrawal_is_journaled_as_not_a_rejection(self):
        self.approve()
        generate.unapprove_candidate("S1", "CAND-0001")
        log = paths.APPROVAL_LOG.read_text(encoding="utf-8")
        self.assertIn("WITHDRAWN", log)
        self.assertIn("not a rejection", log)


class TheGatesBehave(SnapshotTests):
    """One breakdown, edited in place. The only thing that refuses is an
    approved take — its own panel for panel fields, the whole sheet for
    board fields (user rulings 2026-08-16)."""

    def lock(self):
        from common import stable_hash
        spec = store.get_spec("S1")
        paths.SPEC_LOCKS.parent.mkdir(parents=True, exist_ok=True)
        paths.SPEC_LOCKS.write_text(json.dumps(
            {"S1": {"hash": stable_hash(spec)}}), encoding="utf-8")
        return spec

    def test_a_locked_sheet_is_edited_in_place_when_nothing_is_approved(self):
        spec = self.lock()
        spec["scene"] = "Rewritten."
        store.save_spec("S1", spec)
        self.assertEqual(store.get_spec("S1")["scene"], "Rewritten.")

    def test_an_unapproved_panel_stays_editable_beside_an_approved_one(self):
        """The whole point of per-panel: P02 is editable while P01 is not."""
        self.approve()
        spec = self.lock()
        spec["panels"][1]["purpose"] = "A different exterior."
        store.save_spec("S1", spec)
        self.assertEqual(store.get_spec("S1")["panels"][1]["purpose"],
                         "A different exterior.")

    def test_an_approved_panel_refuses_and_names_the_way_through(self):
        self.approve()
        spec = self.lock()
        spec["panels"][0]["purpose"] = "Something else."
        with self.assertRaises(PermissionError) as e:
            store.save_spec("S1", spec)
        self.assertIn("CAND-0001", str(e.exception))
        self.assertIn("Withdraw", str(e.exception))

    def test_board_fields_freeze_once_any_panel_is_approved(self):
        self.approve()
        spec = self.lock()
        spec["scene"] = "Rewritten under an approved take."
        with self.assertRaises(PermissionError) as e:
            store.save_spec("S1", spec)
        self.assertIn("board-level", str(e.exception))
        self.assertIn("P01", str(e.exception))

    def test_an_approved_panel_cannot_be_removed(self):
        self.approve()
        spec = self.lock()
        spec["panels"] = [p for p in spec["panels"] if p["id"] != "P01"]
        with self.assertRaises(PermissionError):
            store.save_spec("S1", spec)

    def test_the_evidence_for_an_approved_panel_is_frozen(self):
        self.approve()
        spec = self.lock()
        for r in spec["evidence_ledger"]:
            if r["panel_id"] == "P01":
                r["source"] = "rewritten citation"
        with self.assertRaises(PermissionError) as e:
            store.save_spec("S1", spec)
        self.assertIn("evidence rows", str(e.exception))

    def test_withdrawing_reopens_everything_that_take_froze(self):
        self.approve()
        generate.unapprove_candidate("S1", "CAND-0001")
        spec = self.lock()
        spec["scene"] = "Now editable again."
        spec["panels"][0]["purpose"] = "And so is the panel."
        store.save_spec("S1", spec)
        out = store.get_spec("S1")
        self.assertEqual(out["scene"], "Now editable again.")
        self.assertEqual(out["panels"][0]["purpose"], "And so is the panel.")

    def test_an_in_place_amend_restamps_and_journals(self):
        spec = self.lock()
        spec["scene"] = "Amended."
        store.save_spec("S1", spec)
        locks = json.loads(paths.SPEC_LOCKS.read_text(encoding="utf-8"))
        self.assertTrue(locks["S1"].get("amended_at"))
        log = paths.APPROVAL_LOG.read_text(encoding="utf-8")
        self.assertIn("amended post-lock", log)
        self.assertIn("scene", log)


class OneGateForEveryEdit(unittest.TestCase):
    """The gate the one-breakdown model needs was already written three
    times over — purpose, camera and content each carried their own copy.
    They are one function now, so the rule cannot drift between them."""

    def test_one_gate_serves_every_panel_edit(self):
        src = (ROOT / "app/store.py").read_text(encoding="utf-8")
        self.assertEqual(src.count("def refuse_if_panel_approved"), 1)
        self.assertGreaterEqual(
            src.count("refuse_if_panel_approved(spec_id, panel_id"), 3,
            "purpose, camera and content all go through it")
        gate = src[src.index("def refuse_if_panel_approved"):]
        gate = gate[:gate.index(chr(10) + "def ")]
        self.assertIn("approved_takes_by_panel(spec_id).get(panel_id", gate,
                      "scoped to THIS panel, not the sheet")
        self.assertIn("Withdraw that approval", gate,
                      "withdrawing is the way through, never rejecting")

    def test_board_fields_freeze_on_the_first_approval(self):
        """User ruling 2026-08-16: board-level fields ride into every
        prompt, so one approved panel freezes them for the sheet."""
        src = (ROOT / "app/store.py").read_text(encoding="utf-8")
        self.assertIn("def refuse_if_any_panel_approved", src)
        self.assertIn("BOARD_LEVEL_FIELDS", src)
        gen = (ROOT / "app/generate.py").read_text(encoding="utf-8")
        self.assertIn("SNAPSHOT_BOARD_FIELDS = store.BOARD_LEVEL_FIELDS", gen,
                      "what an approval freezes and what the gate protects "
                      "must be one list")


if __name__ == "__main__":
    unittest.main()
