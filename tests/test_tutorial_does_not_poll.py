"""An idle tab must not talk to the server.

Found by the user, 2026-08-25, reading uvicorn's log: two idle tabs were
making about five requests a second against a studio nobody was touching.

The cause was a closed loop in the tutorial runtime, and every link in it
was individually reasonable:

    app.js fires `sb:api` after every successful call, so a tutorial step
      can know the user did the thing it asked for
    tutorial.js re-arms trigger evaluation on `sb:api`, so a tutorial
      starts as soon as it becomes eligible
    evaluating a trigger makes API calls, because the predicates ask the
      server what is true

Which closes: evaluate → fetch → sb:api → evaluate. The one shipped
trigger is `not first_run AND not stage_summary.screenplay`, so the loop
armed itself for every user who had finished the first-run tour and
uploaded a screenplay — which is every real user — and ran for as long as
the tab stayed open.

Measured on a tab reproducing that state: 49 × GET /api/projects and 13 ×
GET /api/state in twenty seconds, from ONE tab. After the fix, zero.

The `first_run` cache below makes it cheaper. It is not the fix, and must
not be mistaken for it: a cache would have made the loop quieter and left
it in place, so the next predicate that fetched anything would have
started it again. The fix is that consideration cannot re-arm itself.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TUT = (ROOT / "app/static/tutorial.js").read_text(encoding="utf-8")


class ConsiderationCannotReArmItself(unittest.TestCase):
    def test_a_probe_does_not_reschedule_the_next_consideration(self):
        i = TUT.index('document.addEventListener("sb:api"')
        seg = " ".join(TUT[i:i + 1400].split())
        self.assertIn("if (!probing) considerLater();", seg)

    def test_every_predicate_read_goes_through_the_probe_wrapper(self):
        """A fetch outside `probe()` reopens the loop, so there must not
        be a bare `api(` inside the predicate layer."""
        start = TUT.index("async function productState()")
        end = TUT.index("async function test(")
        seg = TUT[start:end]
        bare = [m for m in re.findall(r"[^e]\bapi\(\"[^\"]+\"\)", seg)
                if "probe(" not in seg[max(0, seg.index(m) - 40):seg.index(m)]]
        self.assertEqual(bare, [], f"unwrapped predicate fetch: {bare}")

    def test_the_probe_restores_its_flag_even_when_the_call_throws(self):
        """A failed /api/state must not leave the engine permanently
        unable to consider anything again."""
        i = TUT.index("async function probe(")
        self.assertIn("finally { probing--; }", TUT[i:i + 200])

    def test_the_two_predicates_that_fetch_both_use_it(self):
        self.assertIn('probe(() => api("/api/state"))', TUT)
        self.assertIn('probe(() => api("/api/projects"))', TUT)


class ASettledQuestionIsNotAskedTwiceASecond(unittest.TestCase):
    def test_first_run_is_cached_like_state(self):
        """It flips false the moment a production exists and only returns
        if every one is deleted."""
        i = TUT.index("async function firstRun()")
        seg = TUT[i:i + 600]
        self.assertIn("firstRunCacheAt < STATE_TTL_MS", seg)

    def test_a_write_clears_both_caches(self):
        """Creating or deleting a production is exactly what changes
        first_run, so a non-GET must not leave a stale answer."""
        i = TUT.index('document.addEventListener("sb:api"')
        self.assertIn("stateCache = firstRunCache = null;", TUT[i:i + 200])

    def test_a_failed_read_does_not_cache_a_guess_forever(self):
        i = TUT.index("async function firstRun()")
        seg = TUT[i:i + 600]
        self.assertIn("catch { firstRunCache = false; }", seg)


class TheEngineStillStartsWhenItShould(unittest.TestCase):
    """The loop must go without taking the feature with it. Consideration
    still runs on the things that actually change the answer: a real API
    call the user caused, and a navigation."""

    def test_a_view_change_still_considers(self):
        i = TUT.index('document.addEventListener("sb:view"')
        self.assertIn("considerLater();", TUT[i:i + 200])

    def test_a_real_user_call_still_considers(self):
        """`probing` is only ever raised around a predicate's own read, so
        a call the user caused still arms the next consideration."""
        i = TUT.index('document.addEventListener("sb:api"')
        seg = TUT[i:i + 1400]
        self.assertIn("considerLater()", seg)
        self.assertEqual(seg.count("probing++"), 0)


if __name__ == "__main__":
    unittest.main()
