"""One board per creative unit (user model, 2026-08-13).

Revision identity, the per-panel revision floor, the qualifying-approval
map the board reads, and the keeps registry. Extended by later phases
with revise-scope guards, slot-map verdicts, and assembly provenance.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import generate, paths, revisions, store  # noqa: E402

_SAVED = {}


def _redirect_home(tmp: Path) -> None:
    _SAVED.update(HOME=paths.HOME, PROJECTS_DIR=paths.PROJECTS_DIR,
                  ACTIVE=paths.ACTIVE_PROJECT_FILE, SETTINGS=paths.SETTINGS,
                  slug=paths.ACTIVE_PROJECT)
    paths.HOME = tmp
    paths.PROJECTS_DIR = tmp / "projects"
    paths.ACTIVE_PROJECT_FILE = tmp / "active_project.json"
    paths.SETTINGS = tmp / "settings.json"
    paths.set_project("")
    paths.ensure_dirs()


def _restore_home() -> None:
    paths.HOME = _SAVED["HOME"]
    paths.PROJECTS_DIR = _SAVED["PROJECTS_DIR"]
    paths.ACTIVE_PROJECT_FILE = _SAVED["ACTIVE"]
    paths.SETTINGS = _SAVED["SETTINGS"]
    paths.set_project(_SAVED["slug"])


def _write_spec(spec_id, panels=("P01", "P02"), scope=None, locked=False):
    spec = {"specification_id": spec_id,
            "revision": revisions.revision_of(spec_id),
            "status": "APPROVED" if locked else "DRAFT",
            "panels": [{"id": p, "purpose": f"{p} purpose"} for p in panels]}
    if scope is not None:
        spec["revision_scope"] = scope
    paths.SPECS_DIR.mkdir(parents=True, exist_ok=True)
    (paths.SPECS_DIR / f"{spec_id}.json").write_text(
        json.dumps(spec), encoding="utf-8")
    if locked:
        locks = {}
        if paths.SPEC_LOCKS.exists():
            locks = json.loads(paths.SPEC_LOCKS.read_text(encoding="utf-8"))
        locks[spec_id] = {"hash": "x" * 32, "approved_at": store.utcnow()}
        paths.SPEC_LOCKS.write_text(json.dumps(locks), encoding="utf-8")
    return spec


def _write_take(spec_id, cand, panel="P01", status="APPROVED"):
    d = paths.BOARDS_DIR / spec_id
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{cand}.json").write_text(json.dumps(
        {"candidate_id": cand, "panel_id": panel, "status": status,
         "specification_id": spec_id}), encoding="utf-8")
    (d / f"{cand}.png").write_bytes(b"png")


class IdentityTests(unittest.TestCase):
    def test_base_and_revision_parsing(self):
        self.assertEqual(revisions.base_of("X_V001_R2"), "X_V001")
        self.assertEqual(revisions.base_of("X_V001"), "X_V001")
        self.assertEqual(revisions.revision_of("X_V001_R7"), 7)
        self.assertEqual(revisions.revision_of("X_V001"), 1)

    def test_revisions_of_is_anchored(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-rev-"))
        _redirect_home(self.tmp)
        try:
            _write_spec("CANYON_X")
            _write_spec("CANYON_X_R2")
            _write_spec("CANYON_XY_R2")  # must NOT be swallowed by CANYON_X
            self.assertEqual(revisions.revisions_of("CANYON_X"),
                             ["CANYON_X", "CANYON_X_R2"])
            self.assertEqual(revisions.revisions_of("CANYON_X_R2"),
                             ["CANYON_X", "CANYON_X_R2"],
                             "any revision id resolves its unit")
        finally:
            _restore_home()


class UnitStateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-rev-"))
        _redirect_home(self.tmp)

    def tearDown(self):
        _restore_home()

    def test_newest_locked_revision_skips_drafts(self):
        _write_spec("U_V001", locked=True)
        _write_spec("U_V001_R2", locked=True,
                    scope={"revised": ["P02"], "carried": ["P01"]})
        _write_spec("U_V001_R3")  # draft
        self.assertEqual(revisions.newest_locked_revision("U_V001"),
                         "U_V001_R2")
        self.assertEqual(revisions.resolve_board_id("U_V001_R3"),
                         ("U_V001", "U_V001_R2"))

    def test_nothing_locked_means_no_structure(self):
        _write_spec("U_V001")
        self.assertIsNone(revisions.newest_locked_revision("U_V001"))

    def test_floor_follows_the_locked_scope(self):
        _write_spec("U_V001", locked=True)
        _write_spec("U_V001_R2", locked=True,
                    scope={"revised": ["P02"], "carried": ["P01"]})
        self.assertEqual(revisions.panel_revision_floor("U_V001", "P01"), 1,
                         "carried panel keeps its old floor")
        self.assertEqual(revisions.panel_revision_floor("U_V001", "P02"), 2)

    def test_a_draft_scope_never_moves_the_floor(self):
        _write_spec("U_V001", locked=True)
        _write_spec("U_V001_R2",
                    scope={"revised": ["P02"], "carried": ["P01"]})  # draft
        self.assertEqual(revisions.panel_revision_floor("U_V001", "P02"), 1)

    def test_legacy_locked_revision_without_scope_revises_everything(self):
        """Pre-feature revisions forked the whole board — the honest floor
        for them is 'all panels revised at that revision'."""
        _write_spec("U_V001", locked=True)
        _write_spec("U_V001_R2", locked=True)  # no scope stored
        self.assertEqual(revisions.panel_revision_floor("U_V001", "P01"), 2)


class QualifyingMapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-qual-"))
        _redirect_home(self.tmp)
        _write_spec("Q_V001", locked=True)
        _write_spec("Q_V001_R2", locked=True,
                    scope={"revised": ["P02"], "carried": ["P01"]})

    def tearDown(self):
        _restore_home()

    def test_carried_panel_qualifies_from_the_old_revision(self):
        _write_take("Q_V001", "CAND-0001", "P01")
        q = revisions.qualifying_approved_by_panel("Q_V001")
        self.assertEqual(q["qualifying"]["P01"]["candidate_id"], "CAND-0001")
        self.assertEqual(q["qualifying"]["P01"]["from_revision"], 1)
        self.assertNotIn("P01", q["offered"])

    def test_revised_panel_demotes_its_old_take_to_offered(self):
        _write_take("Q_V001", "CAND-0002", "P02")
        q = revisions.qualifying_approved_by_panel("Q_V001")
        self.assertNotIn("P02", q["qualifying"])
        self.assertEqual(q["offered"]["P02"][0]["candidate_id"], "CAND-0002")

    def test_newest_qualifying_wins(self):
        _write_take("Q_V001_R2", "CAND-0003", "P02")
        _write_take("Q_V001_R2", "CAND-0010", "P02")
        q = revisions.qualifying_approved_by_panel("Q_V001")
        self.assertEqual(q["qualifying"]["P02"]["candidate_id"], "CAND-0010")

    def test_keep_seats_a_below_floor_take(self):
        _write_take("Q_V001", "CAND-0002", "P02")
        revisions.set_keep("Q_V001", "P02", "CAND-0002")
        q = revisions.qualifying_approved_by_panel("Q_V001")
        self.assertEqual(q["qualifying"]["P02"]["candidate_id"], "CAND-0002")
        self.assertTrue(q["qualifying"]["P02"]["kept"])
        self.assertNotIn("P02", q["offered"], "a kept take stops being offered")
        self.assertIn("KEPT CAND-0002",
                      paths.APPROVAL_LOG.read_text(encoding="utf-8"))

    def test_a_qualifying_take_supersedes_the_keep(self):
        _write_take("Q_V001", "CAND-0002", "P02")
        revisions.set_keep("Q_V001", "P02", "CAND-0002")
        _write_take("Q_V001_R2", "CAND-0009", "P02")
        q = revisions.qualifying_approved_by_panel("Q_V001")
        self.assertEqual(q["qualifying"]["P02"]["candidate_id"], "CAND-0009")
        self.assertFalse(q["qualifying"]["P02"]["kept"])
        self.assertTrue(q["qualifying"]["P02"]["kept_superseded"])

    def test_keep_validation(self):
        _write_take("Q_V001", "CAND-0002", "P02", status="REJECTED")
        with self.assertRaises(ValueError):
            revisions.set_keep("Q_V001", "P02", "CAND-0002")  # not approved
        _write_take("Q_V001_R2", "CAND-0003", "P02")
        with self.assertRaises(ValueError):
            revisions.set_keep("Q_V001", "P02", "CAND-0003")  # already qualifies
        with self.assertRaises(KeyError):
            revisions.set_keep("Q_V001", "P02", "CAND-0404")

    def test_unapproving_a_kept_take_never_resurrects_it(self):
        _write_take("Q_V001", "CAND-0002", "P02")
        revisions.set_keep("Q_V001", "P02", "CAND-0002")
        _write_take("Q_V001", "CAND-0002", "P02", status="REJECTED")
        q = revisions.qualifying_approved_by_panel("Q_V001")
        self.assertNotIn("P02", q["qualifying"])

    def test_clear_keep_journals_and_the_slot_asks_again(self):
        _write_take("Q_V001", "CAND-0002", "P02")
        revisions.set_keep("Q_V001", "P02", "CAND-0002")
        revisions.clear_keep("Q_V001", "P02")
        q = revisions.qualifying_approved_by_panel("Q_V001")
        self.assertNotIn("P02", q["qualifying"])
        self.assertEqual(q["offered"]["P02"][0]["candidate_id"], "CAND-0002")
        self.assertIn("keep of CAND-0002 cleared",
                      paths.APPROVAL_LOG.read_text(encoding="utf-8"))


class ReviseScopeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-scope-"))
        _redirect_home(self.tmp)
        _write_spec("S_V001", locked=True)

    def tearDown(self):
        _restore_home()

    def test_revise_stores_the_scope_and_journals_it(self):
        clone = store.revise_spec("S_V001", ["P02"])
        self.assertEqual(clone["revision_scope"],
                         {"revised": ["P02"], "carried": ["P01"]})
        log = paths.APPROVAL_LOG.read_text(encoding="utf-8")
        self.assertIn("revising: P02", log)
        self.assertIn("carried read-only: P01", log)

    def test_no_selection_means_all_revised(self):
        clone = store.revise_spec("S_V001")
        self.assertEqual(clone["revision_scope"]["revised"], ["P01", "P02"])
        self.assertEqual(clone["revision_scope"]["carried"], [])

    def test_empty_selection_is_a_layout_only_revision(self):
        clone = store.revise_spec("S_V001", [])
        self.assertEqual(clone["revision_scope"]["carried"], ["P01", "P02"])

    def test_unknown_panel_is_refused(self):
        with self.assertRaises(ValueError):
            store.revise_spec("S_V001", ["P99"])

    def test_carried_panels_are_read_only_on_save(self):
        store.revise_spec("S_V001", ["P02"])
        draft = store.get_spec("S_V001_R2")
        draft["panels"][0]["purpose"] = "changed"  # P01 is carried
        with self.assertRaises(ValueError) as ctx:
            store.save_spec("S_V001_R2", draft)
        self.assertIn("P01 is carried read-only", str(ctx.exception))

    def test_carried_panels_cannot_be_removed(self):
        store.revise_spec("S_V001", ["P02"])
        draft = store.get_spec("S_V001_R2")
        draft["panels"] = [p for p in draft["panels"] if p["id"] != "P01"]
        with self.assertRaises(ValueError) as ctx:
            store.save_spec("S_V001_R2", draft)
        self.assertIn("cannot be removed", str(ctx.exception))

    def test_revised_panels_edit_freely_and_scope_is_server_owned(self):
        store.revise_spec("S_V001", ["P02"])
        draft = store.get_spec("S_V001_R2")
        draft["panels"][1]["purpose"] = "a new brief"
        draft["revision_scope"] = {"revised": ["P01", "P02"], "carried": []}
        saved = store.save_spec("S_V001_R2", draft)
        self.assertEqual(saved["panels"][1]["purpose"], "a new brief")
        self.assertEqual(saved["revision_scope"]["carried"], ["P01"],
                         "a save may not rewrite the scope declaration")

    def test_also_revise_upgrades_one_way_and_journals(self):
        store.revise_spec("S_V001", ["P02"])
        scope = store.upgrade_revision_panel("S_V001_R2", "P01")
        self.assertIn("P01", scope["revised"])
        self.assertNotIn("P01", scope["carried"])
        self.assertIn("P01 upgraded into the revision",
                      paths.APPROVAL_LOG.read_text(encoding="utf-8"))
        with self.assertRaises(ValueError):
            store.upgrade_revision_panel("S_V001_R2", "P01")  # already revised
        draft = store.get_spec("S_V001_R2")
        draft["panels"][0]["purpose"] = "changed"
        store.save_spec("S_V001_R2", draft)  # now legal

    def test_amend_verbs_refuse_carried_panels(self):
        store.revise_spec("S_V001", ["P02"])
        with self.assertRaises(PermissionError):
            store.amend_panel_purpose("S_V001_R2", "P01", "new brief")
        with self.assertRaises(PermissionError):
            store.amend_panel_camera("S_V001_R2", "P01",
                                     {"camera_orientation": "SIDE"})
        with self.assertRaises(PermissionError):
            store.amend_panel_content("S_V001_R2", "P01",
                                      add_required=["a thing"])
        store.amend_panel_purpose("S_V001_R2", "P02", "revised brief")  # ok

    def test_a_panel_added_inside_a_scoped_revision_counts_as_revised(self):
        store.revise_spec("S_V001", ["P02"])
        out = store.add_panel("S_V001_R2", "NEW", "a brand new panel")
        scope = store.get_spec("S_V001_R2")["revision_scope"]
        self.assertIn(out["id"], scope["revised"])


if __name__ == "__main__":
    unittest.main()
