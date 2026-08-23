"""An admin's text edit reaches every studio at the next redeploy.

User 2026-08-23. Before this, `text_overrides.json` lived in the install's
own HOME — the comment in main.py said so plainly, "install-level … never
in backups" — so an edit made on one studio reached nobody, survived no
volume replacement, and was invisible to the downloadable app. The store's
equivalent already propagated (one Postgres, one service); the app's did
not, and nothing said which was which.

Two layers now:

  SHIPPED  app/content/ui_text.json — source, rides every deploy, lands on
           every studio and every downloadable copy.
  LOCAL    <HOME>/text_overrides.json — this install only, a scratchpad.

The local layer wins on conflict so an editor always sees their own words,
and `publish` promotes local onto shipped. Because a tenant's filesystem is
not the repo, publish writes where it can and hands back the JSON where it
cannot — it never reports success for an edit that reached one volume.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")


def route_body(decorator: str) -> str:
    """One route's source, bounded by the next decorator rather than by a
    character count — a fixed window drifts into the NEXT handler and then
    asserts about the wrong function."""
    i = MAIN.index(decorator)
    j = MAIN.index(chr(10) + "@app.", i + 1)
    return MAIN[i:j]


def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


class TheTwoLayers(unittest.TestCase):
    def setUp(self):
        from app import main, paths
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self._home = paths.HOME
        paths.HOME = self.home
        self.shipped = self.home / "shipped.json"
        self._shipped_fn = main._shipped_text_path
        main._shipped_text_path = lambda: self.shipped

    def tearDown(self):
        from app import main, paths
        paths.HOME = self._home
        main._shipped_text_path = self._shipped_fn
        self.tmp.cleanup()

    def test_shipped_alone_is_served(self):
        self.shipped.write_text(json.dumps({"Old": "New"}), encoding="utf-8")
        r = client().get("/api/debug/text-overrides").json()
        self.assertEqual(r["overrides"], {"Old": "New"})
        self.assertEqual(r["local"], {})

    def test_local_wins_over_shipped(self):
        """The editor must always see their own edit, or they cannot tell
        whether a rewrite took."""
        self.shipped.write_text(json.dumps({"Old": "Shipped"}), encoding="utf-8")
        (self.home / "text_overrides.json").write_text(
            json.dumps({"Old": "Mine"}), encoding="utf-8")
        r = client().get("/api/debug/text-overrides").json()
        self.assertEqual(r["overrides"]["Old"], "Mine")
        self.assertEqual(r["shipped"]["Old"], "Shipped")

    def test_the_read_is_open(self):
        """A customer's studio renders published copy whether or not its
        owner has debug tools on. Gating the READ would mean a paying
        studio quietly showed the pre-edit wording."""
        self.assertNotIn("_require_debug_tools()",
                         route_body('@app.get("/api/debug/text-overrides")'))

    def test_the_writes_are_still_gated(self):
        for verb in ('@app.put("/api/debug/text-overrides")',
                     '@app.delete("/api/debug/text-overrides")',
                     '@app.post("/api/debug/text-overrides/publish")'):
            self.assertIn("_require_debug_tools()", route_body(verb), verb)

    def test_a_corrupt_layer_does_not_take_the_other_down(self):
        self.shipped.write_text("{not json", encoding="utf-8")
        (self.home / "text_overrides.json").write_text(
            json.dumps({"A": "B"}), encoding="utf-8")
        r = client().get("/api/debug/text-overrides").json()
        self.assertEqual(r["overrides"], {"A": "B"})


class PublishPromotesLocalToSource(unittest.TestCase):
    def setUp(self):
        from app import generate, main, paths
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self._home = paths.HOME
        self._dbg = generate.debug_tools_enabled
        paths.HOME = self.home
        generate.debug_tools_enabled = lambda: True
        self.shipped = self.home / "src" / "ui_text.json"
        self._shipped_fn = main._shipped_text_path
        main._shipped_text_path = lambda: self.shipped

    def tearDown(self):
        from app import generate, main, paths
        paths.HOME = self._home
        generate.debug_tools_enabled = self._dbg
        main._shipped_text_path = self._shipped_fn
        self.tmp.cleanup()

    def _local(self, d):
        (self.home / "text_overrides.json").write_text(
            json.dumps(d), encoding="utf-8")

    def test_it_writes_local_into_source(self):
        self._local({"Old": "New"})
        r = client().post("/api/debug/text-overrides/publish").json()
        self.assertTrue(r["published"])
        self.assertEqual(json.loads(self.shipped.read_text(encoding="utf-8")),
                         {"Old": "New"})

    def test_it_says_a_commit_is_still_needed(self):
        """Writing source is not shipping it — nothing here touches git."""
        self._local({"A": "B"})
        r = client().post("/api/debug/text-overrides/publish").json()
        self.assertIn("commit", r["detail"].lower())
        self.assertIn("deploy", r["detail"].lower())

    def test_publishing_keeps_earlier_published_copy(self):
        """A second editor's publish must not wipe the first's."""
        self.shipped.parent.mkdir(parents=True, exist_ok=True)
        self.shipped.write_text(json.dumps({"First": "One"}), encoding="utf-8")
        self._local({"Second": "Two"})
        client().post("/api/debug/text-overrides/publish")
        self.assertEqual(json.loads(self.shipped.read_text(encoding="utf-8")),
                         {"First": "One", "Second": "Two"})

    def test_an_identity_rewrite_never_reaches_source(self):
        """A string replaced by itself is noise that would sit in the repo
        forever."""
        self._local({"Same": "Same", "Real": "Changed"})
        client().post("/api/debug/text-overrides/publish")
        self.assertEqual(json.loads(self.shipped.read_text(encoding="utf-8")),
                         {"Real": "Changed"})

    def test_an_unwritable_source_refuses_and_hands_back_the_json(self):
        """THE case this exists for. On a hosted studio the repo is not the
        filesystem, so publish must not report success — an admin has to
        know their words landed on one volume and nowhere else."""
        from app import main
        blocker = self.home / "not-a-dir"
        blocker.write_text("i am a file", encoding="utf-8")
        main._shipped_text_path = lambda: blocker / "sub" / "ui_text.json"
        self._local({"A": "B"})
        r = client().post("/api/debug/text-overrides/publish").json()
        self.assertFalse(r["published"])
        self.assertEqual(r["overrides"], {"A": "B"})
        self.assertIn("commit", r["detail"].lower())

    def test_clearing_touches_only_the_local_layer(self):
        self.shipped.parent.mkdir(parents=True, exist_ok=True)
        self.shipped.write_text(json.dumps({"Kept": "Published"}), encoding="utf-8")
        self._local({"Gone": "Local"})
        r = client().delete("/api/debug/text-overrides").json()
        self.assertEqual(r["local"], {})
        self.assertEqual(r["shipped"], {"Kept": "Published"})


class TheUiOffersIt(unittest.TestCase):
    def test_there_is_a_publish_control(self):
        self.assertIn('id="dbg-text-publish"', HTML)
        self.assertIn("Publish to every studio", HTML)

    def test_it_states_both_outcomes(self):
        i = JS.index('$("#dbg-text-publish").onclick')
        seg = JS[i:i + 1400]
        self.assertIn("if (r.published)", seg)
        self.assertIn("cannot write its own source", seg)

    def test_a_refusal_shows_the_json_to_commit(self):
        i = JS.index('$("#dbg-text-publish").onclick')
        self.assertIn("JSON.stringify(r.overrides, null, 2)", JS[i:i + 1400])

    def test_the_client_loads_overrides_whether_or_not_it_can_edit(self):
        """The half that makes publishing mean anything. Editing is gated on
        `_debugTools`; LOADING must not be, or published copy would render
        only on the owner's own machines — the exact opposite of the point.
        Verified at runtime 2026-08-23 on a debug-off install: the original
        string was gone and the published one on screen."""
        i = JS.index("loadTextOverrides().then(")
        line_start = JS.rindex(chr(10), 0, i)
        self.assertNotIn("_debugTools", JS[line_start:i],
                         "the boot load must not be gated on debug tools")
        body = JS[JS.index("async function loadTextOverrides()"):]
        self.assertNotIn("_debugTools", body[:body.index("function applyTextOverrides")])

    def test_the_drawer_does_not_contradict_its_own_button(self):
        """The panel said edits "live on this install only" directly above a
        button reading Publish to every studio. A gate has to be readable as
        state before it is hit — including the gate on publishing itself,
        which on a hosted studio can only ever refuse."""
        i = HTML.index("Page text editing")
        panel = HTML[i:HTML.index("dbg-text-count", i)]
        self.assertNotIn("live on this install only", panel)
        self.assertIn("starts on <b>this install only</b>", panel)
        flat = " ".join(panel.split())
        self.assertIn("rides the next deploy to every studio", flat)
        self.assertIn("needs a writable checkout", flat)
        self.assertIn("on a hosted studio it writes nothing", flat)

    def test_the_shipped_file_exists_in_source(self):
        """It rides every deploy, so it must be in the repo even when
        empty — a missing file is a deploy that carries nothing."""
        self.assertTrue((ROOT / "app/content/ui_text.json").exists())


if __name__ == "__main__":
    unittest.main()
