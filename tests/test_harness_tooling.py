"""HARNESS tooling (2026-08-13): the fixture recorder and the replay
harness builder.

The contract under test: a normal session has NO trace of the recorder;
the builder ships the frontend byte-identical with only the documented
index.html edits; fixtures replay verbatim; the coverage report is
honest about what a recording walk missed."""
from __future__ import annotations

import importlib.util
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

STATIC = ROOT / "app" / "static"
INDEX = (STATIC / "index.html").read_text(encoding="utf-8")
RECORDER = (STATIC / "recorder.js").read_text(encoding="utf-8")

spec = importlib.util.spec_from_file_location(
    "build_harness", ROOT / "tools" / "build_harness.py")
bh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bh)


def synthetic_bundle() -> dict:
    """A recorder-SHAPED bundle for exercising the builder. Test-only —
    the rule that fixtures handed to the designer are recorded, never
    authored, is about the deliverable, not about unit tests."""
    return {
        "recorded_at": "2026-08-13T00:00:00Z",
        "app_sha": "abc1234",
        "project_slug": "beltminers",
        "entries": [
            {"key": "GET /api/projects", "method": "GET",
             "url": "/api/projects", "seq": 0, "status": 200,
             "kind": "json", "body": {"active": "beltminers",
                                      "projects": [], "first_run": False}},
            {"key": "GET /api/state", "method": "GET", "url": "/api/state",
             "seq": 0, "status": 200, "kind": "json", "body": {}},
            {"key": "GET /api/specs/SPEC-0004", "method": "GET",
             "url": "/api/specs/SPEC-0004", "seq": 0, "status": 200,
             "kind": "json", "body": {"id": "SPEC-0004"}},
        ],
    }


class RecorderLoaderTests(unittest.TestCase):
    def test_normal_load_has_no_recorder(self):
        """recorder.js may be referenced ONLY inside the ?record=1 guard —
        an unconditional tag would put a fetch wrapper in every session."""
        refs = [m.start() for m in re.finditer(r'src="/recorder\.js"', INDEX)]
        self.assertEqual(len(refs), 1, "exactly one recorder.js src ref")
        guard = INDEX.find('has("record")')
        self.assertGreater(guard, -1, "the ?record=1 guard exists")
        self.assertLess(0, refs[0] - guard,
                        "the reference sits inside the guarded script")
        self.assertLess(refs[0] - guard, 200,
                        "the reference sits inside the guarded script")

    def test_recorder_loads_before_app_js(self):
        """Load order is the whole trick: fetch must be wrapped before
        boot() runs."""
        self.assertLess(INDEX.find("recorder.js"),
                        INDEX.find('<script src="/app.js">'))

    def test_recorder_records_api_traffic_only(self):
        self.assertIn('url.startsWith("/api/")', RECORDER)

    def test_chip_speaks_the_design_system(self):
        """The chip styles inline (styles.css must stay untouched by a
        dev-only tool) but still through tokens: Courier voice, --hold
        border (R16: dev tooling may not borrow amber) — machine data in the machine voice."""
        for decl in ("font-family:var(--mono)", "border:1px solid var(--hold)",
                     "background:var(--panel)", "border-radius:0"):
            self.assertIn(decl, RECORDER, f"recorder chip: missing '{decl}'")

    def test_recorder_never_authors_fixtures(self):
        """The bundle is built from the log alone — recorded, never
        authored. The recorder must not fabricate response bodies."""
        self.assertIn("entries: log", RECORDER)


class BuilderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-harness-"))
        self.bundle_path = self.tmp / "fixtures-test.json"
        self.bundle_path.write_text(json.dumps(synthetic_bundle()),
                                    encoding="utf-8")
        self.out = self.tmp / "harness"
        bh.build(self.bundle_path, self.out)

    def test_shipped_code_is_byte_identical(self):
        for name in ("app.js", "styles.css"):
            self.assertEqual((self.out / name).read_bytes(),
                             (STATIC / name).read_bytes(), name)

    def test_index_refs_are_relative(self):
        html = (self.out / "index.html").read_text(encoding="utf-8")
        self.assertNotIn('href="/styles.css"', html)
        self.assertNotIn('src="/app.js"', html)
        self.assertNotIn('"/icons/', html)
        self.assertIn('href="styles.css"', html)
        self.assertIn('href="icons/icon.svg"', html)

    def test_fixture_scripts_load_before_app_js(self):
        html = (self.out / "index.html").read_text(encoding="utf-8")
        data = html.find('<script src="fixtures.data.js"></script>')
        shim = html.find('<script src="fixtures.js"></script>')
        app = html.find('<script src="app.js"></script>')
        self.assertTrue(-1 < data < shim < app,
                        "fixtures.data.js, then fixtures.js, then app.js")

    def test_fixtures_ship_as_js_not_bare_json(self):
        # file: origins cannot fetch() a bare fixtures.json
        data = (self.out / "fixtures.data.js").read_text(encoding="utf-8")
        self.assertTrue(data.startswith("window.__FIXTURES__ = "))
        self.assertIn("window.__HARNESS__ = ", data)

    def test_manifest(self):
        m = json.loads((self.out / "MANIFEST.json").read_text(
            encoding="utf-8"))
        self.assertEqual(m["app_sha"], "abc1234")
        self.assertEqual(m["project_slug"], "beltminers")
        self.assertEqual(m["entry_count"], 3)
        self.assertTrue(m["harness_sha"])

    def test_placeholder_is_loud_and_concrete(self):
        svg = (self.out / "icons" / "harness-placeholder.svg").read_text(
            encoding="utf-8")
        self.assertIn("NO FIXTURE IMAGE", svg)
        self.assertIn("Courier", svg)
        self.assertNotIn("var(--", svg,
                         "a standalone SVG cannot resolve CSS variables")

    def test_shim_guards_history_state(self):
        """file: origins throw SecurityError on server-absolute history
        URLs (app.js syncUrl) — uncaught, boot dies with an empty view.
        The shim absorbs it; app.js itself stays byte-identical."""
        shim = (self.out / "fixtures.js").read_text(encoding="utf-8")
        self.assertIn('"pushState", "replaceState"', shim)

    def test_shim_initialises_the_misses_list(self):
        # The plan's sketch pushed to __HARNESS_MISSES__ without ever
        # creating it — every miss would then throw instead of logging.
        shim = (self.out / "fixtures.js").read_text(encoding="utf-8")
        self.assertIn("window.__HARNESS_MISSES__ = []", shim)

    def test_rejects_a_non_bundle(self):
        bad = self.tmp / "not-a-bundle.json"
        bad.write_text("{}", encoding="utf-8")
        with self.assertRaises(SystemExit):
            bh.build(bad, self.tmp / "h2")


class CoverageTests(unittest.TestCase):
    def test_routes_are_parsed_from_main_py(self):
        routes = bh.api_routes((ROOT / "app" / "main.py").read_text(
            encoding="utf-8"))
        self.assertIn(("GET", "/api/healthz"), routes)
        self.assertIn(("GET", "/api/specs/{spec_id}"), routes)
        self.assertGreater(len(routes), 50)

    def test_path_params_normalise(self):
        """A recorded /api/specs/SPEC-0004 covers /api/specs/{spec_id} —
        and must NOT cover deeper routes under the same prefix."""
        routes = [("GET", "/api/specs/{spec_id}"),
                  ("GET", "/api/specs/{spec_id}/revisions"),
                  ("GET", "/api/projects")]
        missed = bh.coverage(synthetic_bundle(), routes)
        self.assertNotIn("GET /api/specs/{spec_id}", missed)
        self.assertIn("GET /api/specs/{spec_id}/revisions", missed)
        self.assertNotIn("GET /api/projects", missed)

    def test_query_strings_do_not_break_matching(self):
        b = synthetic_bundle()
        b["entries"].append({"key": "GET /api/storage?slug=x",
                             "method": "GET", "url": "/api/storage?slug=x",
                             "seq": 0, "status": 200, "kind": "json",
                             "body": {}})
        missed = bh.coverage(b, [("GET", "/api/storage")])
        self.assertEqual(missed, [])


if __name__ == "__main__":
    unittest.main()
