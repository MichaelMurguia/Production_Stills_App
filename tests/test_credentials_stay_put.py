"""A pasted API key must not leave the machine it was pasted on.

Written from an audit on 2026-08-23 (user: "we ask people to paste their
API key in the app to load their own model, is that secure for them?
Prove it"). Most of the guarantees held under live probing — the key never
echoes from any route, never rides a backup, never reaches a release zip,
and the app makes no outbound call to us at all. Two things did not, and
both are pinned here.

FINDING 1 — the flight recorder redacted by FIELD NAME only.
The request middleware writes `str(e)[:500]` on a raised route and the
response body on any 4xx/5xx, both under the key "error". `error` matches
no marker, so anything inside it was written verbatim. That is reachable
without a hostile actor: a custom engine's `base_url` is user-supplied, and
an upstream that echoes the credential in its error message — careless
gateways do — puts the key into `data/activity_log.jsonl`, which rides a
project backup, which we describe to users as shareable creative work.
Proven end to end with a local endpoint before the fix; these tests are
that proof, frozen.

FINDING 2 — `scripts/export_package.py` walked the whole worktree.
It zipped every file under the repo root, and on a standalone install
`SCREENBOARD_HOME` IS the repo root — so `settings.json` with live keys was
in it, along with `.claude/settings.local.json`, 1716 files of `data/`, and
`project_state/`. Nothing had shipped from it, but CLAUDE.md states that
boundary as hard, and the script pointed straight at it."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class TheFlightRecorderScrubsValuesNotJustFieldNames(unittest.TestCase):
    """FINDING 1."""

    def setUp(self):
        from app import paths
        self.tmp = tempfile.TemporaryDirectory()
        home = Path(self.tmp.name)
        self._old = (paths.HOME, paths.SETTINGS, paths.DATA)
        paths.HOME = home
        paths.SETTINGS = home / "settings.json"
        paths.DATA = home / "data"
        paths.DATA.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        from app import paths
        paths.HOME, paths.SETTINGS, paths.DATA = self._old
        self.tmp.cleanup()

    def _store(self, settings: dict):
        from app import paths
        paths.SETTINGS.write_text(json.dumps(settings), encoding="utf-8")

    def test_a_stored_key_is_scrubbed_out_of_any_string(self):
        from app import activity
        self._store({"openai_api_key": "sk-STOREDKEY-abcdefghijklmnop"})
        out = activity._redact(
            {"error": "Error code: 401 - invalid credential Bearer "
                      "sk-STOREDKEY-abcdefghijklmnop"})
        self.assertNotIn("sk-STOREDKEY", out["error"])
        self.assertIn("[redacted]", out["error"])

    def test_a_custom_engines_key_is_scrubbed_too(self):
        """The likeliest path of the two: the user chose that endpoint, so
        the endpoint's error text is not ours to trust."""
        from app import activity
        self._store({"custom_engines": [
            {"id": "e", "api_key": "sk-ENGINEKEY-abcdefghijklmnop"}]})
        out = activity._redact({"error": "bad key sk-ENGINEKEY-abcdefghijklmnop"})
        self.assertNotIn("ENGINEKEY", out["error"])

    def test_a_key_being_tested_is_scrubbed_before_it_is_ever_stored(self):
        """The Test button verifies a credential WITHOUT saving it first, so
        at the moment it can fail there is nothing on disk to match against.
        Shape has to carry that case."""
        from app import activity
        self._store({})
        out = activity._redact({"error": "rejected sk-proj-AAAAAAAAAAAAAAAAAAAA"})
        self.assertNotIn("sk-proj-AAAA", out["error"])
        out = activity._redact({"error": "google said AIzaSyAAAAAAAAAAAAAAAAAAAAAAAA"})
        self.assertNotIn("AIzaSy", out["error"])

    def test_it_reaches_into_nesting_and_lists(self):
        from app import activity
        self._store({"openai_api_key": "sk-DEEPKEY-abcdefghijklmnopqr"})
        out = activity._redact(
            {"detail": {"upstream": ["ok", "died on sk-DEEPKEY-abcdefghijklmnopqr"]}})
        self.assertNotIn("DEEPKEY", json.dumps(out))

    def test_ordinary_text_survives_untouched(self):
        """A flight recorder that mangles its own diagnostics is worse than
        one that leaks — the leak is rare, the debrief is every day."""
        from app import activity
        self._store({"openai_api_key": "sk-REALKEY-abcdefghijklmnopqr"})
        for plain in ("the disk is full", "spec TEST_V001 is locked",
                      "panel FINAL_CONFRONTATION_SAL_TOM has no approved take",
                      "HTTP 503 from the provider"):
            self.assertEqual(activity._redact({"error": plain})["error"], plain)

    def test_a_shorter_key_inside_a_longer_one_cannot_leave_a_usable_tail(self):
        from app import activity
        self._store({"openai_api_key": "sk-AAAABBBBCCCCDDDDEEEE",
                     "gemini_api_key": "sk-AAAABBBBCCCCDDDDEEEEFFFFGGGG"})
        out = activity._redact({"error": "sk-AAAABBBBCCCCDDDDEEEEFFFFGGGG"})
        self.assertEqual(out["error"], "[redacted]")

    def test_the_field_name_rule_still_holds(self):
        from app import activity
        self._store({})
        out = activity._redact({"api_key": "anything", "nested": {"my_token": "t"}})
        self.assertEqual(out["api_key"], "[redacted]")
        self.assertEqual(out["nested"]["my_token"], "[redacted]")

    def test_the_written_line_is_clean_end_to_end(self):
        """The whole chain, as the middleware drives it."""
        from app import activity, paths
        self._store({"openai_api_key": "sk-ENDTOEND-abcdefghijklmnop"})
        activity.log({"method": "POST", "path": "/api/panels/X/generate",
                      "status": 500,
                      "error": "401 invalid credential Bearer "
                               "sk-ENDTOEND-abcdefghijklmnop"})
        written = (paths.DATA / "activity_log.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("ENDTOEND", written)
        self.assertIn("[redacted]", written)

    def test_a_broken_settings_file_does_not_disable_scrubbing(self):
        """`_configured_secrets` reads settings on every call. If that read
        throws, shape matching must still run — failing open here means the
        one corrupt install is also the one that logs keys."""
        from app import activity, paths
        paths.SETTINGS.write_text("{not json", encoding="utf-8")
        out = activity._redact({"error": "died on sk-proj-BBBBBBBBBBBBBBBBBBBB"})
        self.assertNotIn("sk-proj-BBBB", out["error"])


class ThePackagerShipsTrackedFilesOnly(unittest.TestCase):
    """FINDING 2."""

    FULL = (ROOT / "scripts/export_package.py").read_text(encoding="utf-8")
    # The module docstring records what the walk used to do, so assertions
    # about behaviour read the CODE, not the history above it.
    SRC = FULL.split('"""', 2)[2]

    def test_it_no_longer_walks_the_worktree(self):
        self.assertNotIn("rglob", self.SRC,
                         "a worktree walk picks up settings.json and data/")

    def test_git_decides_what_is_shareable(self):
        """Not a hand-kept exclusion list — those drift, and the drift is
        silent until it is someone's API key."""
        self.assertIn("git", self.SRC)
        self.assertIn("ls-files", self.SRC)
        self.assertIn("--exclude-standard", self.SRC)

    def test_it_refuses_rather_than_trims(self):
        """If a forbidden path ever does become tracked, the zip must not be
        written quietly minus that file — someone has to look at it."""
        from scripts import export_package as ep
        self.assertTrue(ep.offenders(["app/main.py", "settings.json"]))
        self.assertTrue(ep.offenders([".claude/settings.local.json"]))
        self.assertTrue(ep.offenders(["projects/x/data/activity_log.jsonl"]))
        self.assertFalse(ep.offenders(["app/main.py", "docs/README.md"]))

    def test_the_real_tree_packages_clean(self):
        from scripts import export_package as ep
        members = ep.tracked_files()
        self.assertFalse(ep.offenders(members))
        self.assertNotIn("settings.json", members)


class TheGuaranteesThatHeld(unittest.TestCase):
    """Verified live during the audit; pinned so they stay true."""

    def test_the_settings_route_returns_a_hint_never_the_key(self):
        main = (ROOT / "app/main.py").read_text(encoding="utf-8")
        i = main.index('@app.get("/api/settings")')
        body = main[i:main.index(chr(10) + "@app.", i + 1)]
        for field in ("openai_api_key", "gemini_api_key", "anthropic_api_key"):
            self.assertIn(f'"{field}_hint"', body)
            self.assertNotIn(f'"{field}": ', body,
                             "the raw key must never be a response field")

    def test_a_backup_excludes_the_legacy_key_file(self):
        bk = (ROOT / "app/backup.py").read_text(encoding="utf-8")
        self.assertIn('rel == "data/settings.json"', bk)
        self.assertIn("continue", bk)

    def test_the_release_artifact_is_built_from_head_not_the_worktree(self):
        """`git archive HEAD -- <six paths>` cannot reach an untracked file,
        so no worktree secret can ride the customer download. This is the
        strongest guarantee in the audit and it is structural."""
        sr = (ROOT / "scripts/stage_release.py").read_text(encoding="utf-8")
        self.assertIn("git", sr)
        self.assertIn("archive", sr)
        self.assertIn("HEAD", sr)
        self.assertIn('INCLUDE = ["app"', sr)
        for forbidden in ("data", "projects", "project_state", "settings.json"):
            self.assertNotIn(f'"{forbidden}"', sr.split("INCLUDE")[1].split("]")[0])

    def test_the_standalone_install_binds_to_loopback(self):
        m = (ROOT / "app/__main__.py").read_text(encoding="utf-8")
        self.assertIn('HOST = "127.0.0.1"', m)
        self.assertNotIn("0.0.0.0", m)

    def test_the_app_never_calls_home(self):
        """Every outbound host must be a model provider the user chose.
        A telemetry endpoint here would make the key's isolation a promise
        rather than a fact."""
        import re
        hosts = set()
        for p in (ROOT / "app").glob("*.py"):
            hosts |= set(re.findall(r"https://([a-zA-Z0-9.-]+)",
                                    p.read_text(encoding="utf-8")))
        # The one non-provider host is OpenRouter's required attribution
        # header, which carries no request payload.
        unexpected = hosts - {"api.anthropic.com", "api.fal.ai", "fal.ai",
                              "openrouter.ai", "queue.fal.run",
                              "www.screenboardstudio.com"}
        self.assertFalse(unexpected, f"new outbound host — audit it: {unexpected}")

    def test_that_one_screenboard_reference_is_only_an_attribution_header(self):
        conn = (ROOT / "app/connectors.py").read_text(encoding="utf-8")
        i = conn.index("screenboardstudio.com")
        self.assertIn("HTTP-Referer", conn[max(0, i - 120):i])


if __name__ == "__main__":
    unittest.main()
