"""The tutorial system: content, vocabulary, and the two places it can rot.

The interesting tests here are not the CRUD ones. They are:

- **the anchor registry** — content names an anchor, `tutorial_schema.json`
  turns it into a selector, and nothing at runtime notices when a selector
  stops matching anything. So the suite resolves every anchor against the
  real markup and JS. A renamed id fails here instead of stranding a
  spotlight on nothing in front of a new customer.
- **one vocabulary, two languages** — Python validates predicates, the
  browser evaluates them. A kind the server accepts and the browser
  ignores is a tutorial that silently never fires; a kind the browser
  handles and the server rejects can never be authored. Both lists are
  read off disk and compared.
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import paths, tutorials  # noqa: E402

JS = (ROOT / "app/static/tutorial.js").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
APPJS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CLIENT = HTML + "\n" + APPJS



def _calls(src: str, fn: str) -> set:
    """Every `fn("name")` in the source, found without a regex — the
    escaping of a word boundary through three layers of quoting is how
    this check silently matched nothing the first time it was written."""
    out, needle = set(), fn + '("'
    i = src.find(needle)
    while i != -1:
        before = src[i - 1] if i else " "
        if not (before.isalnum() or before in "_$."):
            j = src.find('")', i + len(needle))
            name = src[i + len(needle):j] if j != -1 else ""
            if name and all(c.isalnum() or c in "-_" for c in name):
                out.add(name)
        i = src.find(needle, i + 1)
    return out


class HomeRedirect(unittest.TestCase):
    """Every test writes to a throwaway home — the real install is never
    touched, and neither is the repo's shipped content."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-tut-"))
        self._home = paths.HOME
        paths.HOME = self.tmp

    def tearDown(self):
        paths.HOME = self._home


# ------------------------------------------------------------ the vocabulary

class VocabularyTests(unittest.TestCase):
    def test_schema_parses_and_declares_the_five_parts(self):
        s = tutorials.schema()
        for key in ("kinds", "surfaces", "predicates", "anchors", "views",
                    "paths", "view_labels"):
            self.assertIn(key, s, f"the schema must declare {key}")

    def test_every_predicate_the_server_accepts_is_evaluated_in_js(self):
        declared = set(tutorials.schema()["predicates"])
        handled = set(re.findall(r'case "([a-z_]+)":', JS))
        missing = declared - handled
        self.assertFalse(
            missing,
            f"tutorial.js does not evaluate {sorted(missing)} — authored "
            "content using them would validate on save and then never fire")

    def test_js_evaluates_nothing_the_schema_does_not_declare(self):
        declared = set(tutorials.schema()["predicates"])
        handled = set(re.findall(r'case "([a-z_]+)":', JS))
        # The switch also carries the event kinds it dispatches on; those
        # are not predicates and are named here so the check stays honest.
        extra = handled - declared - {"api", "view", "click"}
        self.assertFalse(
            extra,
            f"tutorial.js handles {sorted(extra)}, which the schema does not "
            "declare — nobody can author it")

    def test_every_predicate_declares_where_it_may_be_used(self):
        for kind, decl in tutorials.schema()["predicates"].items():
            self.assertTrue(decl.get("use"), f"{kind}: missing 'use'")
            for ctx in decl["use"]:
                self.assertIn(ctx, ("trigger", "skip_if", "advance"),
                              f"{kind}: unknown context {ctx}")
            self.assertIn("label", decl, f"{kind}: the editor needs a label")
            self.assertIn("hint", decl, f"{kind}: the editor needs a hint")


class TheEditorReadsWhatItDraws(unittest.TestCase):
    """Caught in use 2026-08-20: transliterating the CMS to its design
    board renamed `.tut-adm-trigger` and dropped the act fields, while
    `collect()` still reached for both. Save died with "Cannot read
    properties of null" — shown in the refusal panel as though the
    author's tutorial were at fault — and a step's `act` would have been
    dropped on the next save. Every field the collector reads must exist
    in the markup that same file renders."""

    ADMIN = (ROOT / "app/static/tutorial-admin.js").read_text(encoding="utf-8")

    def test_every_field_it_reads_is_a_field_it_draws(self):
        drawn = set(re.findall(r'data-f="([\w-]+)"', self.ADMIN))
        read = _calls(self.ADMIN, "f")
        self.assertTrue(read, "no header fields found — the scan is broken")
        self.assertFalse(read - drawn, f"collect() reads {sorted(read - drawn)}, "
                                       "which the editor never renders")

    def test_every_step_field_it_reads_is_a_step_field_it_draws(self):
        drawn = set(re.findall(r'data-sf="([\w-]+)"', self.ADMIN))
        read = _calls(self.ADMIN, "g")
        self.assertTrue(read, "no step fields found — the scan is broken")
        self.assertFalse(read - drawn, f"collect() reads {sorted(read - drawn)}, "
                                       "which the step card never renders")

    def test_a_missing_field_names_itself(self):
        self.assertIn("this is a bug in the editor, not in your tutorial",
                      self.ADMIN)

    def test_the_act_survives_an_edit(self):
        """It is deleted from the working copy and rebuilt from the form,
        so the form must carry it."""
        self.assertIn('data-sf="actlabel"', self.ADMIN)
        self.assertIn('data-sf="actgoto"', self.ADMIN)


class AnchorRegistryTests(unittest.TestCase):
    """The registry is the reason authored content survives a redesign —
    which only holds while its selectors still match the app."""

    def test_anchor_names_are_unique(self):
        names = [a["name"] for a in tutorials.anchors()]
        self.assertEqual(len(names), len(set(names)), "duplicate anchor name")

    def test_every_anchor_selector_matches_real_markup(self):
        misses = []
        for a in tutorials.anchors():
            sel = a["selector"]
            ids = re.findall(r"#([A-Za-z0-9_-]+)", sel)
            classes = re.findall(r"\.([A-Za-z0-9_-]+)", sel)
            attrs = re.findall(r"\[([a-z-]+)=([A-Za-z0-9_-]+)\]", sel)
            ok = True
            for i in ids:
                if f'id="{i}"' not in CLIENT:
                    ok = False
            for c in classes:
                if f'"{c}"' not in CLIENT and f"{c}" not in CLIENT:
                    ok = False
            for name, val in attrs:
                if f'{name}="{val}"' not in CLIENT:
                    ok = False
            if not ok:
                misses.append(f"{a['name']} → {sel}")
        self.assertFalse(
            misses,
            "these anchors no longer match anything in the app — every "
            "tutorial pointing at them would fall back to a centred modal:\n"
            + "\n".join(misses))

    def test_views_named_in_the_schema_are_real_views(self):
        for v in tutorials.schema()["views"]:
            self.assertIn(f'"{v}"', APPJS, f"unknown view {v}")

    def test_paths_named_in_the_schema_are_real_routes(self):
        """The URL vocabulary and the internal view names differ (the band
        was renamed after the router was written), so the editor offers
        paths from a list — which has to be the router's list."""
        m = re.search(r"const VIEW_PATH = \{(.*?)\};", APPJS, re.S)
        self.assertTrue(m, "VIEW_PATH not found in app.js")
        real = {"/" + p for p in re.findall(r'"([a-z-]+)"', m.group(1))}
        for p in tutorials.schema()["paths"]:
            self.assertIn(p, real, f"{p} is not a route this app serves")


# ------------------------------------------------------------- shipped content

class ShippedContentTests(unittest.TestCase):
    def test_every_packaged_tutorial_validates(self):
        files = list(tutorials.PACKAGED.glob("*.json"))
        self.assertTrue(files, "no packaged tutorials — the FTUE is gone")
        for f in files:
            doc = json.loads(f.read_text(encoding="utf-8"))
            self.assertEqual(doc.get("id"), f.stem,
                             f"{f.name}: id must match the filename")
            self.assertFalse(tutorials.validate(doc),
                             f"{f.name}: {tutorials.validate(doc)}")

    def test_the_ftue_exists_and_is_live(self):
        ftue = json.loads(
            (tutorials.PACKAGED / "first-board.json").read_text(encoding="utf-8"))
        self.assertTrue(ftue["enabled"])
        self.assertTrue(ftue["trigger"], "an FTUE with no trigger never runs")

    def test_the_ftue_waits_for_a_production_to_exist(self):
        """Caught 2026-08-17 by walking the arrival flow: the FTUE fired on
        a brand-new install, over the app's own 'name the show' screen —
        the welcome modal covered the name field and the Create button, and
        its next step would have spotlit a band that is hidden there. An
        empty install is already onboarding; the walkthrough waits its
        turn."""
        ftue = json.loads(
            (tutorials.PACKAGED / "first-board.json").read_text(encoding="utf-8"))
        self.assertIn({"not": {"first_run": True}},
                      ftue["trigger"].get("all", []),
                      "the FTUE must not run before a production exists")

    def test_the_example_announcement_ships_disabled(self):
        """It is a template to duplicate, not a message for the fleet."""
        ex = json.loads((tutorials.PACKAGED / "example-release-note.json")
                        .read_text(encoding="utf-8"))
        self.assertFalse(ex["enabled"])


# ---------------------------------------------------------------- validation

class ValidationTests(unittest.TestCase):
    def good(self):
        return {"id": "t1", "rev": 1, "kind": "flow", "title": "T",
                "steps": [{"surface": "modal", "title": "Hello"}]}

    def test_a_good_document_passes(self):
        self.assertEqual(tutorials.validate(self.good()), [])

    def test_unknown_field_is_refused(self):
        doc = self.good()
        doc["stpes"] = []
        self.assertTrue(any("unknown field" in e for e in tutorials.validate(doc)))

    def test_a_spotlight_needs_a_known_anchor(self):
        doc = self.good()
        doc["steps"] = [{"surface": "spotlight", "title": "x"}]
        self.assertTrue(any("anchor" in e for e in tutorials.validate(doc)))
        doc["steps"][0]["anchor"] = "no.such.thing"
        self.assertTrue(any("anchor" in e for e in tutorials.validate(doc)))
        doc["steps"][0]["anchor"] = "band"
        self.assertEqual(tutorials.validate(doc), [])

    def test_a_predicate_is_refused_in_a_context_it_cannot_work_in(self):
        """`first_run` as an advance condition would leave the step waiting
        forever — the whole point of declaring contexts."""
        doc = self.good()
        doc["steps"][0]["advance"] = {"first_run": True}
        errs = tutorials.validate(doc)
        self.assertTrue(any("cannot be used as advance" in e for e in errs), errs)

    def test_api_advance_needs_a_valid_pattern(self):
        doc = self.good()
        doc["steps"][0]["advance"] = {"api": {"method": "POST", "path": "^/api/x"}}
        self.assertEqual(tutorials.validate(doc), [])
        doc["steps"][0]["advance"] = {"api": {"method": "POST", "path": "([unclosed"}}
        self.assertTrue(any("valid pattern" in e for e in tutorials.validate(doc)))

    def test_goto_cannot_leave_the_app(self):
        doc = self.good()
        for bad in ("https://evil.example/x", "//evil.example", "evil"):
            doc["steps"][0]["goto"] = bad
            self.assertTrue(tutorials.validate(doc),
                            f"{bad} must not be an accepted destination")
        doc["steps"][0]["goto"] = "/settings"
        self.assertEqual(tutorials.validate(doc), [])

    def test_a_blank_step_is_refused(self):
        doc = self.good()
        doc["steps"] = [{"surface": "modal"}]
        self.assertTrue(any("title or a body" in e for e in tutorials.validate(doc)))

    def test_nested_conditions_are_checked_through(self):
        doc = self.good()
        doc["trigger"] = {"all": [{"state": "a.b"}, {"click": "band"}]}
        errs = tutorials.validate(doc)
        self.assertTrue(any("click" in e for e in errs),
                        "a click is an event — it cannot be a trigger")

    def test_id_shape(self):
        for bad in ("", "Has Caps", "../escape", "a/b"):
            doc = self.good()
            doc["id"] = bad
            self.assertTrue(tutorials.validate(doc), f"{bad!r} must be refused")


# ---------------------------------------------------------- merge and state

class ResolutionTests(HomeRedirect):
    def test_install_content_overrides_packaged_by_id(self):
        d = tutorials.install_dir()
        d.mkdir(parents=True, exist_ok=True)
        (d / "first-board.json").write_text(json.dumps({
            "id": "first-board", "rev": 9, "kind": "flow", "title": "Mine",
            "steps": [{"surface": "modal", "title": "x"}]}), encoding="utf-8")
        rows = {t["id"]: t for t in tutorials.resolved()}
        self.assertEqual(rows["first-board"]["title"], "Mine")
        self.assertEqual(rows["first-board"]["source"], "install")
        self.assertTrue(rows["first-board"]["overrides_packaged"])

    def test_a_tombstone_hides_a_packaged_tutorial(self):
        d = tutorials.install_dir()
        d.mkdir(parents=True, exist_ok=True)
        (d / "first-board.json").write_text(
            json.dumps({"id": "first-board", "deleted": True}), encoding="utf-8")
        self.assertNotIn("first-board", [t["id"] for t in tutorials.resolved()])

    def test_broken_content_is_inert_not_half_run(self):
        d = tutorials.install_dir()
        d.mkdir(parents=True, exist_ok=True)
        (d / "broken.json").write_text(json.dumps({
            "id": "broken", "kind": "flow", "title": "B",
            "steps": [{"surface": "spotlight", "anchor": "gone", "title": "x"}]}),
            encoding="utf-8")
        self.assertIn("broken", [t["id"] for t in tutorials.resolved()])
        self.assertNotIn("broken", [t["id"] for t in tutorials.live()])

    def test_a_corrupt_file_does_not_take_the_others_down(self):
        d = tutorials.install_dir()
        d.mkdir(parents=True, exist_ok=True)
        (d / "junk.json").write_text("{not json", encoding="utf-8")
        self.assertTrue(tutorials.resolved())

    def test_priority_orders_the_queue(self):
        d = tutorials.install_dir()
        d.mkdir(parents=True, exist_ok=True)
        for tid, pri in (("low", 1), ("high", 500)):
            (d / f"{tid}.json").write_text(json.dumps({
                "id": tid, "kind": "flow", "title": tid, "priority": pri,
                "steps": [{"surface": "modal", "title": "x"}]}), encoding="utf-8")
        ids = [t["id"] for t in tutorials.resolved()]
        self.assertLess(ids.index("high"), ids.index("low"))


class StateTests(HomeRedirect):
    def test_record_and_resume(self):
        tutorials.record("first-board", "seen", 2, 1)
        row = tutorials.load_state()["tutorials"]["first-board"]
        self.assertEqual(row["status"], "seen")
        self.assertEqual(row["step"], 2)
        self.assertTrue(row["first_seen"])
        tutorials.record("first-board", "completed", 4, 1)
        row = tutorials.load_state()["tutorials"]["first-board"]
        self.assertEqual(row["status"], "completed")
        self.assertTrue(row["version"], "the version is what an announcement "
                                        "compares against")

    def test_reset_one_and_all(self):
        tutorials.record("a", "completed", 1, 1)
        tutorials.record("b", "completed", 1, 1)
        tutorials.reset("a")
        self.assertNotIn("a", tutorials.load_state()["tutorials"])
        self.assertIn("b", tutorials.load_state()["tutorials"])
        tutorials.reset()
        self.assertEqual(tutorials.load_state()["tutorials"], {})

    def test_a_bad_status_is_refused(self):
        with self.assertRaises(ValueError):
            tutorials.record("a", "vibes", 0, 1)

    def test_a_traversing_id_is_refused(self):
        with self.assertRaises(KeyError):
            tutorials.record("../../etc/passwd", "seen", 0, 1)

    def test_the_bundle_carries_what_the_runtime_needs(self):
        b = tutorials.export_bundle()
        for key in ("tutorials", "state", "version", "anchors"):
            self.assertIn(key, b)
        self.assertTrue(b["anchors"], "the runtime cannot resolve a spotlight "
                                      "without the anchor map")


class SaveTests(HomeRedirect):
    def setUp(self):
        super().setUp()
        # Force the studio branch: saving must never write the repo from a
        # test run.
        self._can = tutorials.can_ship
        tutorials.can_ship = lambda: False

    def tearDown(self):
        tutorials.can_ship = self._can
        super().tearDown()

    def test_save_validates_before_writing(self):
        with self.assertRaises(ValueError):
            tutorials.save({"id": "x", "kind": "flow", "title": "x", "steps": []})
        self.assertFalse((tutorials.install_dir() / "x.json").exists())

    def test_save_then_read_back(self):
        tutorials.save({"id": "x", "kind": "flow", "title": "X", "rev": 2,
                        "steps": [{"surface": "modal", "title": "hi"}]})
        got = tutorials.get("x")
        self.assertEqual(got["title"], "X")
        self.assertEqual(got["source"], "install")
        self.assertTrue(got["updated"])

    def test_delete_of_a_packaged_id_leaves_a_tombstone(self):
        tutorials.delete("first-board")
        self.assertNotIn("first-board", [t["id"] for t in tutorials.resolved()])
        self.assertTrue((tutorials.install_dir() / "first-board.json").exists())


if __name__ == "__main__":
    unittest.main()
