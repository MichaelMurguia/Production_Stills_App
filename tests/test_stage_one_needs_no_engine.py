"""Uploading a screenplay costs nothing, so it does not wait for a key.

User, 2026-09-01: "product is locked. I added key and cant access the
screenplay tab."

Their key WAS saved. The dev loop sets SCREENBOARD_NO_KEYS so a mis-click
in a fast local loop cannot spend money, and the app honours it by
blanking its own stored credentials. Two consequences met:

1. `any_credential` went false, and a ruling of 2026-08-18 locked EVERY
   stage on that — including the screenplay, which needs no engine at all.
   Uploading a draft spends nothing; the READ spends, and the read has its
   own gate. The tab was refusing the one thing it could have done for
   free. **The user amended that ruling on 2026-09-01: stage 01 no longer
   waits.**

2. The app reported the exact shape of an un-configured install, so every
   surface sent them to Settings to add the key that was sitting there
   saved. A gate must name the condition it is ACTUALLY enforcing, so
   `capability` now reports `keys_suppressed` and the popover says so.

The second half is why this was worth fixing rather than documenting: the
app told someone to do something they had already done.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import generate  # noqa: E402

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
NL = chr(10)


class StageOneDoesNotWaitForAnEngine(unittest.TestCase):
    def seg(self):
        i = JS.index("With no model connected the pipeline waits")
        return JS[i:JS.index("for (const stage of STAGE_ORDER)", i)]

    def test_everything_downstream_still_locks(self):
        s = self.seg()
        self.assertIn("if (state.capability && !state.capability.any_credential) {", s)
        self.assertIn("forEach(s2 => lockedStages.add(s2))", s)

    def test_but_the_screenplay_does_not(self):
        self.assertIn('STAGE_ORDER.filter(s2 => s2 !== "screenplay")', self.seg())

    def test_the_amendment_is_recorded_where_the_ruling_was(self):
        """A later pass reading only the old comment would put it back."""
        s = self.seg()
        self.assertIn("2026-08-18", s)
        self.assertIn("amended by the user 2026-09-01", s)

    def test_the_sentence_no_longer_claims_every_stage_needs_a_model(self):
        i = JS.index("const NO_MODEL_SENTENCE =")
        seg = JS[i:i + 200]
        self.assertIn("Everything past the screenplay", seg)
        self.assertNotIn("Every stage runs on an AI model", seg)


class TheGateNamesTheConditionItEnforces(unittest.TestCase):
    def test_capability_reports_the_dev_guard(self):
        was = os.environ.get("SCREENBOARD_NO_KEYS")
        try:
            os.environ["SCREENBOARD_NO_KEYS"] = "1"
            self.assertTrue(generate.capability()["keys_suppressed"])
            del os.environ["SCREENBOARD_NO_KEYS"]
            self.assertFalse(generate.capability()["keys_suppressed"])
        finally:
            if was is None:
                os.environ.pop("SCREENBOARD_NO_KEYS", None)
            else:
                os.environ["SCREENBOARD_NO_KEYS"] = was

    def test_the_popover_says_the_key_is_saved_rather_than_missing(self):
        i = JS.index("const KEYS_SUPPRESSED_SENTENCE =")
        seg = JS[i:i + 400]
        self.assertIn("Your key is saved", seg)
        self.assertIn("cannot spend", seg)

    def test_it_names_the_command_that_lifts_it(self):
        """A gate states its remedy. And the remedy has to be typeable —
        `\\d` is not a JS escape, so the backslash was silently dropped
        and the sentence read `.dev.bat`, which is not a command."""
        i = JS.index("const KEYS_SUPPRESSED_SENTENCE =")
        seg = JS[i:i + 400]
        self.assertIn(chr(92) + chr(92) + "dev.bat --keys", seg)

    def test_the_two_sentences_are_chosen_by_the_real_condition(self):
        i = JS.index("const noModelSentence = () =>")
        seg = JS[i:i + 300]
        self.assertIn("_bandState?.capability?.keys_suppressed", seg)
        self.assertIn("KEYS_SUPPRESSED_SENTENCE : NO_MODEL_SENTENCE", seg)

    def test_the_popover_asks_for_the_sentence_rather_than_the_constant(self):
        """Otherwise the branch above is dead code."""
        self.assertIn("? noModelSentence()", JS)
        self.assertEqual(JS.count("NO_MODEL_SENTENCE"), 2,
                         "one definition, one use inside the chooser")




class SettingsStopsOfferingAuthenticateForAKeyItHas(unittest.TestCase):
    """User, 2026-09-01: "my api key is not saving. If I add the key and
    save it — everything still says NO ENGINE and the open AI section does
    not register it."

    It was saving every time. The dev loop blanks stored credentials so a
    mis-click cannot spend, and does it by making the process unable to
    see them rather than by editing the file — so the row rendered exactly
    like an install with no key, offered Authenticate, and the user added
    theirs again.

    The same guard produced the same confusion on 2026-08-16 (a stale PASS
    badge beside an invisible key). That fix marked the TEST stale. This
    one marks the ROW."""

    def test_an_engine_reports_whether_its_key_is_being_hidden(self):
        i = JS.index("const supp = (engAll[r.key] || {}).suppressed;")
        seg = JS[i:i + 900]
        self.assertIn("KEY SAVED &mdash; HIDDEN BY THIS DEV SESSION", seg)

    def test_that_row_does_not_offer_to_authenticate(self):
        """Offering it is the error — it is what sent the user round the
        loop."""
        i = JS.index("const supp = (engAll[r.key] || {}).suppressed;")
        seg = JS[i:JS.index("if (!r.connected && !r.custom) return `", i)]
        self.assertNotIn('data-act="auth"', seg)
        self.assertIn("RESTART WITH", seg)

    def test_the_remedy_is_typeable(self):
        i = JS.index("RESTART WITH")
        self.assertIn(chr(92) + chr(92) + "dev.bat --keys", JS[i:i + 120])

    def test_a_genuinely_keyless_row_still_offers_authenticate(self):
        """The guard is the exception, not the new default."""
        i = JS.index("const supp = (engAll[r.key] || {}).suppressed;")
        rest = JS[JS.index("if (!r.connected && !r.custom) return `", i):]
        self.assertIn('data-act="auth">Authenticate', rest[:600])

    def test_the_flag_is_false_when_no_key_is_stored(self):
        import os
        was = os.environ.get("SCREENBOARD_NO_KEYS")
        try:
            os.environ["SCREENBOARD_NO_KEYS"] = "1"
            # This process has no dev home configured in the test run, so
            # nothing is stored and nothing can be suppressed.
            for e in generate.engine_credentials().values():
                self.assertIn("suppressed", e)
        finally:
            if was is None:
                os.environ.pop("SCREENBOARD_NO_KEYS", None)
            else:
                os.environ["SCREENBOARD_NO_KEYS"] = was

    def test_the_raw_read_never_hands_back_a_value(self):
        """`_raw_settings` bypasses the guard AND decryption. It exists to
        answer "is there a key on disk", and must never become a way to
        read one the guard is refusing."""
        src = (ROOT / "app/generate.py").read_text(encoding="utf-8")
        i = src.index("    suppressed = set()")
        seg = src[i:src.index("gkey = s.get(", i)]
        self.assertIn("suppressed.add(pid)", seg)
        # Only the presence of the field is ever taken from it.
        self.assertIn('if str(raw.get(field, "")).strip():', seg)
        self.assertNotIn("raw[field]", seg)


class AConcurrentReadNoLongerFailsTheWrite(unittest.TestCase):
    """Found while chasing an intermittent failure of the cinematography
    concurrency test — about one full-suite run in five, and present
    before any of today's changes.

    On Windows `os.replace` raises PermissionError [WinError 5] when any
    other handle holds the DESTINATION open, including a reader part-way
    through `read_text`. So the concurrent read did not get stale data —
    it made the WRITE fail. In a studio that is a lost ID allocation or a
    lost app-state save."""

    def test_eight_threads_reading_and_writing_raise_nothing(self):
        import tempfile as tf
        import threading
        from app import paths, store
        was = dict(HOME=paths.HOME, PROJECTS_DIR=paths.PROJECTS_DIR,
                   ACTIVE=paths.ACTIVE_PROJECT_FILE, SETTINGS=paths.SETTINGS,
                   slug=paths.ACTIVE_PROJECT)
        tmp = tf.TemporaryDirectory()
        try:
            t = Path(tmp.name)
            paths.HOME = t
            paths.PROJECTS_DIR = t / "projects"
            paths.ACTIVE_PROJECT_FILE = t / "active_project.json"
            paths.SETTINGS = t / "settings.json"
            paths.set_project("")
            paths.ensure_dirs()
            errs = []

            def hammer():
                try:
                    for _ in range(150):
                        store.load_app_state()
                        store.next_counter("t", "T")
                except Exception as e:      # noqa: BLE001
                    errs.append(repr(e))

            ts = [threading.Thread(target=hammer) for _ in range(8)]
            [x.start() for x in ts]
            [x.join() for x in ts]
            self.assertEqual(errs, [], errs)
        finally:
            paths.HOME = was["HOME"]
            paths.PROJECTS_DIR = was["PROJECTS_DIR"]
            paths.ACTIVE_PROJECT_FILE = was["ACTIVE"]
            paths.SETTINGS = was["SETTINGS"]
            paths.set_project(was["slug"])
            tmp.cleanup()

    def test_the_retry_is_bounded(self):
        """A file held open for good must reach the caller as an error
        rather than spin."""
        src = (ROOT / "app/store.py").read_text(encoding="utf-8")
        self.assertIn("for attempt in range(_REPLACE_TRIES):", src)
        self.assertIn("if attempt == _REPLACE_TRIES - 1:", src)
        self.assertIn("raise", src)

    def test_only_a_permission_error_is_retried(self):
        """A disk-full or a bad path is not a race and must not be slept
        on eight times."""
        src = (ROOT / "app/store.py").read_text(encoding="utf-8")
        i = src.index("for attempt in range(_REPLACE_TRIES):")
        self.assertIn("except PermissionError:", src[i:i + 400])


if __name__ == "__main__":
    unittest.main()
