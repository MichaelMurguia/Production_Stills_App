"""Rejection notes survive their takes (user ruling 2026-08-13).

The user deleted a rejected take and its carried note vanished from the
rail — it was still carrying (the archive fed the prompt) but only live
records were rendered, so it LOOKED destroyed. The contract now: the
rail renders exactly what carries (carried_feedback), a note is edited
in place by its Edit verb, and it is deleted ONLY by its own Delete verb
— never as a side effect. Deleting a take archives the note, retired
flag included.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import generate, paths, store  # noqa: E402

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


def _write_take(spec_id, cand, panel="P01", status="REJECTED",
                reason="no neon signage", retired=False):
    d = paths.BOARDS_DIR / spec_id
    d.mkdir(parents=True, exist_ok=True)
    rec = {"candidate_id": cand, "panel_id": panel, "status": status,
           "status_reason": reason}
    if retired:
        rec["feedback_retired"] = True
    (d / f"{cand}.json").write_text(json.dumps(rec), encoding="utf-8")
    (d / f"{cand}.png").write_bytes(b"png")


class NoteLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-notes-"))
        _redirect_home(self.tmp)

    def tearDown(self):
        _restore_home()

    def test_deleting_a_take_keeps_its_note_carrying_and_visible(self):
        _write_take("SPEC_A", "CAND-0001")
        generate.delete_candidate("SPEC_A", "CAND-0001")
        self.assertIn("no neon signage",
                      generate.rejection_feedback("SPEC_A", "P01"),
                      "the note must keep carrying after the take dies")
        items = generate.carried_feedback("SPEC_A")
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0]["archived"],
                        "the rail must SHOW the archived note — invisible "
                        "reads as destroyed")
        self.assertEqual(items[0]["source"], "CAND-0001")

    def test_a_retired_note_stays_retired_through_deletion(self):
        _write_take("SPEC_A", "CAND-0001", retired=True)
        generate.delete_candidate("SPEC_A", "CAND-0001")
        self.assertNotIn("no neon signage",
                         generate.rejection_feedback("SPEC_A", "P01"),
                         "deletion must not resurrect a retired note")
        self.assertTrue(generate.carried_feedback("SPEC_A")[0]["retired"])

    def test_edit_rewrites_a_live_note_in_place(self):
        _write_take("SPEC_A", "CAND-0001")
        generate.edit_feedback("SPEC_A", "CAND-0001", "no holograms")
        self.assertEqual(generate.rejection_feedback("SPEC_A", "P01"),
                         ["no holograms"])
        self.assertIn("rejection note edited",
                      paths.APPROVAL_LOG.read_text(encoding="utf-8"))

    def test_edit_rewrites_an_archived_note(self):
        _write_take("SPEC_A", "CAND-0001")
        generate.delete_candidate("SPEC_A", "CAND-0001")
        generate.edit_feedback("SPEC_A", "CAND-0001", "no holograms")
        self.assertEqual(generate.rejection_feedback("SPEC_A", "P01"),
                         ["no holograms"])

    def test_an_empty_edit_is_refused_not_a_silent_delete(self):
        _write_take("SPEC_A", "CAND-0001")
        with self.assertRaises(generate.GenerationError):
            generate.edit_feedback("SPEC_A", "CAND-0001", "   ")
        self.assertEqual(generate.rejection_feedback("SPEC_A", "P01"),
                         ["no neon signage"])

    def test_delete_verb_removes_a_live_note_but_keeps_the_take(self):
        _write_take("SPEC_A", "CAND-0001")
        generate.delete_feedback("SPEC_A", "CAND-0001")
        self.assertEqual(generate.rejection_feedback("SPEC_A", "P01"), [])
        rec = generate.get_candidate("SPEC_A", "CAND-0001")
        self.assertEqual(rec["status"], "REJECTED",
                         "the take and its status survive; only the note goes")
        self.assertIn("DELETED by the user",
                      paths.APPROVAL_LOG.read_text(encoding="utf-8"))

    def test_delete_verb_removes_an_archived_note(self):
        _write_take("SPEC_A", "CAND-0001")
        generate.delete_candidate("SPEC_A", "CAND-0001")
        generate.delete_feedback("SPEC_A", "CAND-0001")
        self.assertEqual(generate.rejection_feedback("SPEC_A", "P01"), [])
        self.assertEqual(generate.carried_feedback("SPEC_A"), [])

    def test_unknown_note_is_a_keyerror(self):
        with self.assertRaises(KeyError):
            generate.edit_feedback("SPEC_A", "CAND-0404", "x")
        with self.assertRaises(KeyError):
            generate.delete_feedback("SPEC_A", "CAND-0404")

    def test_carried_list_spans_revisions_and_both_sources(self):
        _write_take("SPEC_B", "CAND-0001")
        generate.delete_candidate("SPEC_B", "CAND-0001")
        _write_take("SPEC_B_R2", "CAND-0002", reason="side view please")
        items = generate.carried_feedback("SPEC_B_R2")
        self.assertEqual([i["source"] for i in items],
                         ["CAND-0002", "CAND-0001"], "newest first")
        self.assertEqual([i["archived"] for i in items], [False, True])


class UiWiringTests(unittest.TestCase):
    JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")

    def test_the_rail_renders_the_carried_list_not_live_records(self):
        self.assertIn("/carried-feedback", self.JS)
        self.assertIn("TAKE DELETED, NOTE CARRIES", self.JS)

    def test_the_rail_offers_two_verbs_only(self):
        """HARNESS_AUDIT R17: Edit + one reversible Stop carrying — never
        two verbs for one outcome. Hard delete left the rail entirely."""
        for probe in ("data-fb-edit", "data-retire"):
            self.assertIn(probe, self.JS)
        self.assertNotIn("data-fb-delete", self.JS,
                         "delete is no longer a rail verb")
        self.assertIn(">Stop carrying</button>", self.JS)

    def test_delete_lives_in_the_edit_modal_and_asks_first(self):
        """R17: the destructive door sits inside the Edit modal, out of
        pointer range, and is still a confirmed journaled act."""
        i = self.JS.index('extraLabel: "Delete forever"')
        seg = self.JS[i:i + 900]
        self.assertIn("askConfirm", seg,
                      "note deletion is an explicit confirmed act")
        self.assertIn("feedback-delete", seg)

    def test_a_stopped_note_reads_as_state_not_history_paint(self):
        """U1: a record has no status colour — the stopped state is a
        stated Courier line, not a struck-through red row."""
        self.assertIn("NOT CARRIED", self.JS)
        css = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
        self.assertNotIn("text-decoration: line-through", css.split(".carried")[1][:400])


if __name__ == "__main__":
    unittest.main()
