"""P1 coverage from docs/TEST_MATRIX.md: the sheet lock/hash contract,
the candidate lifecycle, and the assemble endpoint — the behaviors that
guard canon, driven through the real routes with fabricated takes (no
model calls anywhere)."""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))  # sibling import under -m unittest too

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app import generate, paths, store  # noqa: E402
import app.main as appmain  # noqa: E402

from test_app_api import _redirect_home, _restore_home  # noqa: E402

FIXTURE = json.loads((ROOT / "examples" / "minimal_valid_spec.json")
                     .read_text(encoding="utf-8"))


def _valid_spec(spec_id: str) -> dict:
    spec = json.loads(json.dumps(FIXTURE))
    spec["specification_id"] = spec_id
    spec["status"] = "DRAFT"
    return spec


class _Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-p1-"))
        _redirect_home(self.tmp)
        self.client = TestClient(appmain.app)
        # Breakdowns gate on a saved Art Direction Bible (423 otherwise).
        r = self.client.put("/api/style-bible", json={
            "text": "## Test Language\nWarm dust, hard sun.\n"})
        assert r.status_code == 200, r.text

    def tearDown(self):
        _restore_home()

    # -- fabricated takes --------------------------------------------------

    def _mk_candidate(self, spec_id: str, panel_id: str, cand_id: str,
                      w: int = 3840, h: int = 2160,
                      status: str = "PROVISIONAL") -> dict:
        d = paths.BOARDS_DIR / spec_id
        d.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (w, h), (90, 80, 70)).save(d / f"{cand_id}.png", "PNG")
        record = {"candidate_id": cand_id, "specification_id": spec_id,
                  "panel_id": panel_id, "status": status,
                  "width": w, "height": h, "spec_hash": "test-hash",
                  "created_at": store.utcnow()}
        (d / f"{cand_id}.json").write_text(
            json.dumps(record, indent=2) + "\n", encoding="utf-8")
        return record

    def _locked_spec(self, spec_id: str) -> dict:
        r = self.client.post("/api/specs", json={
            "specification_id": spec_id, "subject": "Lifecycle test"})
        self.assertEqual(r.status_code, 200, r.text)
        r = self.client.put(f"/api/specs/{spec_id}", json=_valid_spec(spec_id))
        self.assertEqual(r.status_code, 200, r.text)
        r = self.client.post(f"/api/specs/{spec_id}/approve")
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()


class SheetLifecycleTests(_Base):
    """The lock/hash contract — the product's core promise."""

    def test_save_guards(self):
        self.client.post("/api/specs", json={
            "specification_id": "P1SAVE_V001", "subject": "s"})
        spec = _valid_spec("P1SAVE_V001")
        # The id may not change on save.
        wrong = {**spec, "specification_id": "OTHER_V001"}
        self.assertEqual(
            self.client.put("/api/specs/P1SAVE_V001", json=wrong).status_code, 422)
        # APPROVED can only be minted by the approve action.
        sneaky = {**spec, "status": "APPROVED"}
        self.assertEqual(
            self.client.put("/api/specs/P1SAVE_V001", json=sneaky).status_code, 422)
        # Saving a spec that doesn't exist is a 404, not a create.
        self.assertEqual(
            self.client.put("/api/specs/P1GHOST_V001",
                            json=_valid_spec("P1GHOST_V001")).status_code, 404)

    def test_approve_mints_lock_and_hash(self):
        spec = self._locked_spec("P1LOCK_V001")
        self.assertEqual(spec["status"], "APPROVED")
        locks = json.loads(paths.SPEC_LOCKS.read_text(encoding="utf-8"))
        self.assertIn("P1LOCK_V001", locks)
        self.assertTrue(locks["P1LOCK_V001"]["hash"])
        r = self.client.get("/api/specs/P1LOCK_V001")
        self.assertTrue(r.json()["locked"])
        # Locked means locked: saves refuse, re-approval refuses.
        self.assertEqual(
            self.client.put("/api/specs/P1LOCK_V001",
                            json=_valid_spec("P1LOCK_V001")).status_code, 423)
        self.assertEqual(
            self.client.post("/api/specs/P1LOCK_V001/approve").status_code, 423)

    def test_approve_refuses_invalid_specs(self):
        self.client.post("/api/specs", json={
            "specification_id": "P1BAD_V001", "subject": "s"})
        bad = _valid_spec("P1BAD_V001")
        # Remove the PASS evidence row for a required object → validator fails.
        bad["evidence_ledger"] = bad["evidence_ledger"][1:]
        self.client.put("/api/specs/P1BAD_V001", json=bad)
        r = self.client.post("/api/specs/P1BAD_V001/approve")
        self.assertEqual(r.status_code, 422)
        self.assertFalse(store.spec_locked("P1BAD_V001"))

    def test_unlock_voids_the_lock_and_reapproval_mints_a_new_hash(self):
        self._locked_spec("P1UNLOCK_V001")
        hash1 = json.loads(paths.SPEC_LOCKS.read_text(
            encoding="utf-8"))["P1UNLOCK_V001"]["hash"]
        r = self.client.post("/api/specs/P1UNLOCK_V001/unlock")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "DRAFT")
        self.assertFalse(store.spec_locked("P1UNLOCK_V001"))
        # Unlocking an unlocked sheet is a stated 422, not a no-op.
        self.assertEqual(
            self.client.post("/api/specs/P1UNLOCK_V001/unlock").status_code, 422)
        # Edit + re-approve mints a NEW hash — provenance never aliases.
        edited = _valid_spec("P1UNLOCK_V001")
        edited["subject"] = "Edited after unlock"
        self.assertEqual(self.client.put(
            "/api/specs/P1UNLOCK_V001", json=edited).status_code, 200)
        self.assertEqual(self.client.post(
            "/api/specs/P1UNLOCK_V001/approve").status_code, 200)
        hash2 = json.loads(paths.SPEC_LOCKS.read_text(
            encoding="utf-8"))["P1UNLOCK_V001"]["hash"]
        self.assertNotEqual(hash1, hash2)

    def test_unlock_and_delete_refuse_while_approved_output_exists(self):
        self._locked_spec("P1CANON_V001")
        self._mk_candidate("P1CANON_V001", "P01", "CAND-9001",
                           status="APPROVED")
        # Approved canon pins the sheet: no unlock, no delete.
        self.assertEqual(
            self.client.post("/api/specs/P1CANON_V001/unlock").status_code, 423)
        self.assertEqual(
            self.client.delete("/api/specs/P1CANON_V001").status_code, 423)
        # Rejecting the output (explicit, journaled) releases the guard.
        r = self.client.post(
            "/api/specs/P1CANON_V001/candidates/CAND-9001/status",
            json={"status": "REJECTED", "reason": "voiding for test"})
        self.assertEqual(r.status_code, 200)
        r = self.client.delete("/api/specs/P1CANON_V001")
        self.assertEqual(r.status_code, 200)
        self.assertFalse((paths.BOARDS_DIR / "P1CANON_V001").exists())
        self.assertIsNone(store.get_spec("P1CANON_V001"))

    def test_revise_clones_a_draft_next_revision(self):
        self._locked_spec("P1REV_V001")
        r = self.client.post("/api/specs/P1REV_V001/revise")
        self.assertEqual(r.status_code, 200)
        clone = r.json()
        self.assertEqual(clone["specification_id"], "P1REV_V001_R2")
        self.assertEqual(clone["revision"], 2)
        self.assertEqual(clone["status"], "DRAFT")
        self.assertEqual(clone["revised_from"]["specification_id"], "P1REV_V001")
        self.assertTrue(clone["revised_from"]["locked"])
        self.assertFalse(store.spec_locked("P1REV_V001_R2"))
        # The original stays locked; re-revising the same target 409s.
        self.assertTrue(store.spec_locked("P1REV_V001"))
        self.assertEqual(
            self.client.post("/api/specs/P1REV_V001/revise").status_code, 409)


class CandidateLifecycleTests(_Base):
    """Judging-room transitions: approve/reject/promote/purge/serve."""

    def setUp(self):
        super().setUp()
        self._locked_spec("P1CAND_V001")

    def _locked_spec(self, spec_id):
        return SheetLifecycleTests._locked_spec(self, spec_id)

    def test_status_transitions_and_rejection_feedback(self):
        self._mk_candidate("P1CAND_V001", "P01", "CAND-9101")
        r = self.client.post(
            "/api/specs/P1CAND_V001/candidates/CAND-9101/status",
            json={"status": "REJECTED", "reason": "horizon tilts left"})
        self.assertEqual(r.status_code, 200)
        rec = generate.get_candidate("P1CAND_V001", "CAND-9101")
        self.assertEqual(rec["status"], "REJECTED")
        self.assertEqual(rec["status_reason"], "horizon tilts left")
        # The reason rides into this panel's future prompts.
        self.assertIn("horizon tilts left",
                      generate.rejection_feedback("P1CAND_V001", "P01"))
        # Invalid status is a stated 422; unknown candidate a 404.
        self.assertEqual(self.client.post(
            "/api/specs/P1CAND_V001/candidates/CAND-9101/status",
            json={"status": "MAYBE"}).status_code, 422)
        self.assertEqual(self.client.post(
            "/api/specs/P1CAND_V001/candidates/CAND-9999/status",
            json={"status": "APPROVED"}).status_code, 404)

    def test_promote_gates_and_back_link(self):
        self._mk_candidate("P1CAND_V001", "P01", "CAND-9102")
        # Only APPROVED renders promote.
        r = self.client.post(
            "/api/specs/P1CAND_V001/candidates/CAND-9102/promote",
            json={"role": "SCENE_REFERENCE"})
        self.assertEqual(r.status_code, 422)
        self.client.post("/api/specs/P1CAND_V001/candidates/CAND-9102/status",
                         json={"status": "APPROVED"})
        # Role is required.
        self.assertEqual(self.client.post(
            "/api/specs/P1CAND_V001/candidates/CAND-9102/promote",
            json={}).status_code, 422)
        r = self.client.post(
            "/api/specs/P1CAND_V001/candidates/CAND-9102/promote",
            json={"role": "SCENE_REFERENCE", "controls": "layout, light"})
        self.assertEqual(r.status_code, 200, r.text)
        ref = r.json()
        self.assertEqual(ref["status"], "APPROVED")
        self.assertEqual(ref["controls"], ["layout", "light"])
        # The take carries the back-link the judging room badges.
        rec = generate.get_candidate("P1CAND_V001", "CAND-9102")
        self.assertEqual(rec["promoted_ref"], ref["id"])
        # And the reference image is the take's pixels, resolvable.
        self.assertIsNotNone(store.reference_image_path(ref["id"]))

    def test_purge_rejected_deletes_only_rejected(self):
        self._mk_candidate("P1CAND_V001", "P01", "CAND-9103",
                           status="REJECTED")
        self._mk_candidate("P1CAND_V001", "P02", "CAND-9104",
                           status="REJECTED")
        self._mk_candidate("P1CAND_V001", "P03", "CAND-9105",
                           status="APPROVED")
        r = self.client.post("/api/specs/P1CAND_V001/candidates/purge-rejected")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(sorted(r.json()["deleted"]),
                         ["CAND-9103", "CAND-9104"])
        left = {c["candidate_id"]
                for c in generate.list_candidates("P1CAND_V001")}
        self.assertEqual(left, {"CAND-9105"})
        # Purged takes stop serving; the survivor still serves.
        self.assertEqual(self.client.get(
            "/api/specs/P1CAND_V001/candidates/CAND-9103/image").status_code, 404)
        self.assertEqual(self.client.get(
            "/api/specs/P1CAND_V001/candidates/CAND-9105/image").status_code, 200)

    def test_image_route_404s_stated(self):
        self.assertEqual(self.client.get(
            "/api/specs/P1CAND_V001/candidates/CAND-0000/image").status_code, 404)
        self.assertEqual(self.client.get(
            "/api/specs/P1CAND_V001/candidates/..%2Fx/image").status_code, 404)


class AssembleRouteTests(_Base):
    """The board pipeline through the API — geometry is unit-tested in
    test_assemble_layout; this drives the route contract."""

    def _ready_spec(self, spec_id, sizes=None):
        SheetLifecycleTests._locked_spec(self, spec_id)
        sizes = sizes or {}
        for i, pid in enumerate(("P01", "P02", "P03"), start=1):
            w, h = sizes.get(pid, (3840, 2160))
            self._mk_candidate(spec_id, pid, f"CAND-92{i:02d}",
                               w=w, h=h, status="APPROVED")

    def test_slot_map_then_assemble_happy_path(self):
        self._ready_spec("P1ASM_V001")
        sm = self.client.get("/api/specs/P1ASM_V001/slot-map").json()
        self.assertTrue(sm["ready"], sm["not_ready"])
        self.assertEqual({s["status"] for s in sm["slots"]}, {"OK"})

        r = self.client.post("/api/specs/P1ASM_V001/assemble",
                             json={"width": 3840, "height": 2160,
                                   "variant": "aspect"})
        self.assertEqual(r.status_code, 200, r.text)
        b = r.json()
        self.assertEqual(b["kind"], "assembled_board")
        self.assertEqual((b["width"], b["height"]), (3840, 2160))
        self.assertEqual(b["layout_variant"], "aspect")
        # The structural-board contract: rects + panels_used for every panel.
        self.assertEqual(set(b["rects"]), {"P01", "P02", "P03"})
        self.assertEqual(set(b["panels_used"]), {"P01", "P02", "P03"})
        self.assertEqual(b["warnings"], [])
        # The 4K composite exists at the recorded size and lists as a board.
        img = paths.BOARDS_DIR / "P1ASM_V001" / f"{b['candidate_id']}.png"
        with Image.open(img) as im:
            self.assertEqual(im.size, (3840, 2160))
        boards = self.client.get("/api/specs/P1ASM_V001/boards").json()
        self.assertIn(b["candidate_id"],
                      [x["candidate_id"] for x in boards])

    def test_too_small_verdict_through_the_api(self):
        self._ready_spec("P1SMALL_V001", sizes={"P02": (400, 300)})
        sm = self.client.get("/api/specs/P1SMALL_V001/slot-map").json()
        self.assertFalse(sm["ready"])
        by_pid = {s["panel_id"]: s for s in sm["slots"]}
        self.assertEqual(by_pid["P02"]["status"], "TOO_SMALL")
        self.assertEqual(by_pid["P01"]["status"], "OK")
        # Assembly still runs (letterboxed, never upscaled) and SAYS so.
        b = self.client.post("/api/specs/P1SMALL_V001/assemble",
                             json={}).json()
        self.assertTrue(any("upscaling" in w for w in b["warnings"]))

    def test_assemble_gates(self):
        # Unlocked spec → 422 with the stated reason.
        self.client.post("/api/specs", json={
            "specification_id": "P1DRAFT_V001", "subject": "s"})
        r = self.client.post("/api/specs/P1DRAFT_V001/assemble", json={})
        self.assertEqual(r.status_code, 422)
        self.assertIn("not approved", r.json()["detail"])
        # Locked but missing takes → 422 naming the gap.
        SheetLifecycleTests._locked_spec(self, "P1EMPTY_V001")
        r = self.client.post("/api/specs/P1EMPTY_V001/assemble", json={})
        self.assertEqual(r.status_code, 422)
        self.assertIn("APPROVED candidate", r.json()["detail"])
        # Unknown spec → 404; out-of-range canvas → 422 (audit bound).
        self.assertEqual(self.client.post(
            "/api/specs/P1NOPE_V001/assemble", json={}).status_code, 404)
        self.assertEqual(self.client.get(
            "/api/specs/P1EMPTY_V001/slot-map",
            params={"width": 60000, "height": 60000}).status_code, 422)


if __name__ == "__main__":
    unittest.main()
