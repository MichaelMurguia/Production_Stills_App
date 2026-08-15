"""Collapsing a revision chain into one breakdown (user ruling 2026-08-16,
"Yes Collapse", asked for concretely 2026-08-16: "I still have 2 CANYON_GRM
breakdowns. Lets consolodate.").

Revisions answered "what was this approved AS?" by forking the document.
The snapshot on each approved take answers it without the fork, so the
chain is now a duplicate of itself — two breakdowns and two panel screens
for one creative unit. These tests pin what the collapse must never lose:
an approved take, its image, its snapshot, or the record of which
revision it came from."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import paths, revisions, store  # noqa: E402

BASE = "CANYON_GRM"
R2 = "CANYON_GRM_R2"


def spec(spec_id: str, scene: str, purpose: str) -> dict:
    return {
        "specification_id": spec_id,
        "subject": "A canyon",
        "mode": "CANON_EXTRACTION",
        "revision": revisions.revision_of(spec_id),
        "scene": scene,
        "render_intent": "Grounded.",
        "panels": [{"id": "P01", "title": "Approach", "purpose": purpose,
                    "required_objects": ["a road"]}],
        "evidence_ledger": [{"panel_id": "P01", "object": "a road",
                             "evidence_class": "SCRIPT_EXPLICIT",
                             "source": "EXT. CANYON: a road.",
                             "status": "PASS"}],
    }


class Chain(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-cons-"))
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
        self.write(BASE, spec(BASE, "The old scene.", "The old purpose."))
        self.write(R2, spec(R2, "The revised scene.", "The revised purpose."))
        # R1 has one approved take; R2 has one approved and one candidate.
        self.take(BASE, "CAND-0001", "APPROVED", approved_spec={
            "board": {"scene": "The old scene."},
            "panel": {"purpose": "The old purpose."}})
        self.take(R2, "CAND-0002", "APPROVED", approved_spec={
            "board": {"scene": "The revised scene."},
            "panel": {"purpose": "The revised purpose."}})
        self.take(R2, "CAND-0003", "CANDIDATE")
        self.lock(R2)

    def tearDown(self):
        (paths.HOME, paths.PROJECTS_DIR, paths.ACTIVE_PROJECT_FILE,
         paths.SETTINGS, slug) = self._saved
        paths.set_project(slug)
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ------------------------------------------------------------- fixtures
    def write(self, spec_id, doc):
        (paths.SPECS_DIR / f"{spec_id}.json").write_text(
            json.dumps(doc), encoding="utf-8")

    def take(self, spec_id, cand_id, status, approved_spec=None):
        d = paths.BOARDS_DIR / spec_id
        d.mkdir(parents=True, exist_ok=True)
        rec = {"candidate_id": cand_id, "specification_id": spec_id,
               "panel_id": "P01", "status": status, "width": 3136,
               "height": 1344}
        if approved_spec:
            rec["approved_spec"] = approved_spec
        (d / f"{cand_id}.json").write_text(json.dumps(rec), encoding="utf-8")
        (d / f"{cand_id}.png").write_bytes(b"PNG" + cand_id.encode())

    def lock(self, spec_id):
        from common import stable_hash
        locks = store._load_locks()
        locks[spec_id] = {"hash": stable_hash(store.get_spec(spec_id)),
                          "approved_at": store.utcnow()}
        store._atomic_write_json(paths.SPEC_LOCKS, locks)

    def rec(self, cand_id):
        p = paths.BOARDS_DIR / BASE / f"{cand_id}.json"
        return json.loads(p.read_text(encoding="utf-8"))


class ThePlanIsReadableBeforeTheAct(Chain):
    def test_it_states_every_revision_and_what_it_holds(self):
        plan = revisions.consolidation_plan(BASE)
        self.assertTrue(plan["can_consolidate"])
        rows = {r["spec_id"]: r for r in plan["revisions"]}
        self.assertEqual(rows[BASE]["takes"], 1)
        self.assertEqual(rows[R2]["takes"], 2)
        self.assertEqual(rows[R2]["approved"], 1)
        self.assertTrue(rows[R2]["locked"])

    def test_the_newest_revision_supplies_the_content(self):
        self.assertEqual(revisions.consolidation_plan(BASE)["content_from"], R2)

    def test_a_single_breakdown_says_so_instead_of_offering_the_act(self):
        (paths.SPECS_DIR / f"{R2}.json").unlink()
        plan = revisions.consolidation_plan(BASE)
        self.assertFalse(plan["can_consolidate"])
        self.assertIn("already one breakdown", plan["why_not"])

    def test_the_plan_reads_the_same_from_any_id_in_the_chain(self):
        self.assertEqual(revisions.consolidation_plan(R2)["base"], BASE)


class TheCollapse(Chain):
    def test_there_is_one_breakdown_afterwards(self):
        revisions.consolidate(BASE)
        self.assertEqual(revisions.revisions_of(BASE), [BASE],
                         "the whole point: one breakdown, not two")
        self.assertFalse((paths.SPECS_DIR / f"{R2}.json").exists())

    def test_the_newest_content_survives_under_the_base_id(self):
        revisions.consolidate(BASE)
        out = store.get_spec(BASE)
        self.assertEqual(out["specification_id"], BASE)
        self.assertEqual(out["scene"], "The revised scene.")
        self.assertEqual(out["panels"][0]["purpose"], "The revised purpose.")

    def test_the_older_document_is_archived_inside_the_breakdown(self):
        """Not deleted, and not left as a file — a file on disk is a
        breakdown the user can open, which is the problem being solved."""
        revisions.consolidate(BASE)
        hist = store.get_spec(BASE)["consolidated_from"]
        self.assertEqual([h["spec_id"] for h in hist], [BASE])
        self.assertEqual(hist[0]["spec"]["scene"], "The old scene.")

    def test_every_take_lands_in_one_pool_with_its_image(self):
        revisions.consolidate(BASE)
        d = paths.BOARDS_DIR / BASE
        for cid in ("CAND-0001", "CAND-0002", "CAND-0003"):
            self.assertTrue((d / f"{cid}.json").exists(), cid)
            self.assertTrue((d / f"{cid}.png").exists(), f"{cid} image")
        self.assertFalse((paths.BOARDS_DIR / R2).exists())

    def test_a_moved_take_is_addressable_at_the_base(self):
        revisions.consolidate(BASE)
        self.assertEqual(self.rec("CAND-0002")["specification_id"], BASE)

    def test_provenance_survives_the_retag(self):
        revisions.consolidate(BASE)
        self.assertEqual(self.rec("CAND-0002")["consolidated_from"], R2)
        self.assertNotIn("consolidated_from", self.rec("CAND-0001"),
                         "a take that never moved was never retagged")

    def test_the_snapshot_a_take_was_approved_against_is_untouched(self):
        """The reason the collapse is safe at all: each take carries the
        document it was approved against, so folding the documents cannot
        rewrite what an approval meant."""
        revisions.consolidate(BASE)
        self.assertEqual(self.rec("CAND-0001")["approved_spec"]["board"]["scene"],
                         "The old scene.")
        self.assertEqual(self.rec("CAND-0002")["approved_spec"]["panel"]["purpose"],
                         "The revised purpose.")

    def test_both_approvals_now_gate_the_one_panel(self):
        revisions.consolidate(BASE)
        self.assertEqual(sorted(store.approved_takes_by_panel(BASE)["P01"]),
                         ["CAND-0001", "CAND-0002"])

    def test_a_locked_chain_stays_locked_and_rehashed(self):
        revisions.consolidate(BASE)
        self.assertTrue(store.spec_locked(BASE))
        self.assertNotIn(R2, store._load_locks())
        from common import stable_hash
        self.assertEqual(store._load_locks()[BASE]["hash"],
                         stable_hash(store.get_spec(BASE)),
                         "a stale hash would read as tampering")

    def test_a_backup_of_every_document_is_written_first(self):
        out = revisions.consolidate(BASE)
        bak = Path(out["backup"])
        self.assertTrue((bak / f"{BASE}.json").exists())
        self.assertTrue((bak / f"{R2}.json").exists())
        self.assertTrue((bak / "locks.json").exists())
        self.assertEqual(
            json.loads((bak / f"{R2}.json").read_text(encoding="utf-8"))["scene"],
            "The revised scene.")

    def test_it_is_journaled_as_the_end_of_revisions(self):
        revisions.consolidate(BASE)
        log = paths.APPROVAL_LOG.read_text(encoding="utf-8")
        self.assertIn("CONSOLIDATED", log)
        self.assertIn(R2, log)
        self.assertIn("Revisions are retired", log)

    def test_consolidating_a_single_breakdown_is_refused_not_a_no_op(self):
        revisions.consolidate(BASE)
        with self.assertRaises(ValueError) as e:
            revisions.consolidate(BASE)
        self.assertIn("already one breakdown", str(e.exception))

    def test_it_is_idempotent_in_effect_when_run_from_the_revision_id(self):
        revisions.consolidate(R2)
        self.assertEqual(revisions.revisions_of(BASE), [BASE])

    def test_a_colliding_take_refuses_before_a_single_file_moves(self):
        """A half-folded board is worse than a refusal."""
        self.take(R2, "CAND-0001", "CANDIDATE")
        with self.assertRaises(FileExistsError):
            revisions.consolidate(BASE)
        self.assertTrue((paths.BOARDS_DIR / R2 / "CAND-0002.json").exists(),
                        "nothing moved")
        self.assertTrue((paths.SPECS_DIR / f"{R2}.json").exists())

    def test_the_keeps_registry_travels_if_it_was_stranded(self):
        (paths.BOARDS_DIR / R2 / "keeps.json").write_text(
            json.dumps({"P01": {"candidate_id": "CAND-0002"}}),
            encoding="utf-8")
        revisions.consolidate(BASE)
        self.assertEqual(revisions.load_keeps(BASE)["P01"]["candidate_id"],
                         "CAND-0002")


class TheBoardStopsSeeingTwoOfEverything(Chain):
    def test_the_take_pool_is_one_pool_keyed_on_the_base(self):
        revisions.consolidate(BASE)
        q = revisions.qualifying_approved_by_panel(BASE)
        self.assertIn("P01", q["qualifying"])
        self.assertEqual(q["offered"], {},
                         "nothing is below a floor when there is one revision")

    def test_the_newest_approved_take_seats_on_the_board(self):
        revisions.consolidate(BASE)
        q = revisions.qualifying_approved_by_panel(BASE)
        self.assertEqual(q["qualifying"]["P01"]["candidate_id"], "CAND-0002")


if __name__ == "__main__":
    unittest.main()
