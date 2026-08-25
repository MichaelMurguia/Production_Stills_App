"""C6 and C9 — two small rules, both about not being fooled.

C6: run-to-run variance is large enough that one take proves nothing.
Twenty renders were read as evidence about a cinematography grammar over
two days, and nobody ever established what two identical runs look like
— because nothing ever rendered the same thing twice. Where the app
invites a comparison it now renders two and shows them together.

C9: nothing checked a prompt's length against what an engine will
accept. No limit has ever been hit — 132 takes from 289 to 21,179
characters all succeeded, which is the measurement that ended the "the
prompt is too long" theory — so the built-in engines state no limit. A
custom engine is a user-supplied endpoint with unknown limits, and a
refusal there arrives from the middle of a paid render.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import generate  # noqa: E402

GEN = (ROOT / "app/generate.py").read_text(encoding="utf-8")
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")


class NoEngineIsGivenALimitNobodyStated(unittest.TestCase):
    """C9. Inventing a limit for the built-ins would be inventing the
    very constraint the measurement disproved."""

    def test_the_built_ins_state_none(self):
        for p in ("gemini", "openai", "openai-chat"):
            self.assertEqual(generate.prompt_limit(p), 0, p)

    def test_an_unknown_engine_states_none(self):
        self.assertEqual(generate.prompt_limit("nope"), 0)
        self.assertEqual(generate.prompt_limit(""), 0)

    def test_junk_in_the_settings_file_states_none(self):
        was = dict(generate.PROVIDERS)
        try:
            generate.PROVIDERS["j"] = {"label": "J", "prompt_limit": "lots"}
            self.assertEqual(generate.prompt_limit("j"), 0)
            generate.PROVIDERS["j"]["prompt_limit"] = -5
            self.assertEqual(generate.prompt_limit("j"), 0)
        finally:
            generate.PROVIDERS.clear()
            generate.PROVIDERS.update(was)

    def test_a_custom_engine_carries_what_its_owner_stated(self):
        self.assertIn('"prompt_limit": e.get("prompt_limit") or 0,', GEN)
        self.assertIn('int(body.get("prompt_limit") or 0)', MAIN)


class TheLimitIsAGateNotAnApiError(unittest.TestCase):
    def setUp(self):
        self.was = dict(generate.PROVIDERS)
        generate.PROVIDERS["fake"] = {"label": "My Endpoint", "model": "m",
                                      "prompt_limit": 100}

    def tearDown(self):
        generate.PROVIDERS.clear()
        generate.PROVIDERS.update(self.was)

    def test_under_the_limit_passes(self):
        generate._require_prompt_fits("fake", "x" * 100)

    def test_over_it_refuses_with_both_numbers(self):
        with self.assertRaises(generate.GenerationError) as e:
            generate._require_prompt_fits("fake", "x" * 101)
        msg = str(e.exception)
        self.assertIn("101", msg)
        self.assertIn("100", msg)
        self.assertIn("My Endpoint", msg)

    def test_it_says_nothing_was_spent(self):
        """The whole point is that the refusal arrives before the money."""
        with self.assertRaises(generate.GenerationError) as e:
            generate._require_prompt_fits("fake", "x" * 999)
        self.assertIn("Nothing has been spent", str(e.exception))

    def test_it_says_the_limit_may_be_the_wrong_number(self):
        """A limit that only says "too long" leaves the user cutting a
        prompt when the honest answer is usually to raise a figure they
        guessed at."""
        with self.assertRaises(generate.GenerationError) as e:
            generate._require_prompt_fits("fake", "x" * 999)
        self.assertIn("raise the engine's stated limit", str(e.exception))

    def test_no_stated_limit_never_refuses(self):
        generate._require_prompt_fits("gemini", "x" * 100_000)

    def test_it_guards_the_path_that_spends(self):
        i = GEN.index('_require_room("this take")')
        self.assertIn("_require_prompt_fits(provider, override or prompt)",
                      GEN[i:i + 500])

    def test_the_panel_states_the_room_before_generate(self):
        """A gate must be readable BEFORE it is hit, not surfaced as an
        error after the user acts."""
        i = JS.index("MADE OF ·")
        self.assertIn("THIS ENGINE ACCEPTS", JS[i - 400:i + 400])

    def test_the_engine_card_states_it_either_way(self):
        """"No stated limit" is a fact, not a blank."""
        self.assertIn("NO STATED PROMPT LIMIT", JS)
        self.assertIn("PROMPTS UP TO ", JS)


class TheProbeRendersTwice(unittest.TestCase):
    """C6."""

    def seg(self):
        i = GEN.index("def sample_probe(")
        return GEN[i:GEN.index("def list_samples(", i)]

    def test_both_runs_are_rendered_from_one_prompt(self):
        s = self.seg()
        self.assertIn('out = _samples_dir() / f"{provider}.png"', s)
        self.assertIn('out_b = _samples_dir() / f"{provider}-b.png"', s)
        self.assertEqual(s.count("_one("), 3)  # the def and two calls

    def test_a_failed_second_run_does_not_throw_away_the_first(self):
        """Half a comparison is worth more than none, and the first
        render was already paid for."""
        s = self.seg()
        self.assertIn('notes_b, pair = f"second run failed', s)
        self.assertIn("out_b.unlink(missing_ok=True)", s)

    def test_the_record_says_whether_it_is_a_pair(self):
        self.assertIn('"pair": pair,', self.seg())

    def test_the_listing_reports_the_second_image_separately(self):
        self.assertIn('meta["has_image_b"]', GEN)

    def test_the_route_serves_the_second_run(self):
        self.assertIn("def api_sample_image(provider: str, run: str = \"a\"):", MAIN)
        self.assertIn("generate.sample_image_path(provider, run)", MAIN)

    def test_a_sample_from_before_the_rule_still_shows(self):
        """One image and a sentence saying so, not a gap where a picture
        should be."""
        i = JS.index("wiz-pair")
        seg = " ".join(JS[i:i + 1600].split())
        self.assertIn("smp.has_image_b ?", seg)
        self.assertIn("nothing here shows this engine's variance", seg)

    def test_the_pair_says_what_the_difference_between_them_means(self):
        i = JS.index("wiz-pair")
        seg = " ".join(JS[i:i + 1600].split())
        self.assertIn("this engine's variance, not a decision it made", seg)

    def test_neither_run_is_shown_as_the_answer(self):
        """Equal size, no hierarchy — making one larger would make it the
        answer, and neither is."""
        block = CSS.split(".wiz-pair {")[1].split("}")[0]
        self.assertIn("grid-template-columns: 1fr 1fr", block)

    def test_a_single_run_does_not_sit_in_half_a_row(self):
        self.assertIn(".wiz-pair:has(> :only-child) { grid-template-columns: 1fr; }", CSS)

    def test_the_button_says_it_renders_twice(self):
        i = JS.index('data-f="regen"')
        self.assertIn("twice from the same prompt", JS[i:i + 300])

    def test_the_wait_is_stated_as_two_takes(self):
        i = JS.index("Rendering ${subject")
        self.assertIn("two runs", JS[i:i + 400])
        self.assertIn("two takes of the same prompt", JS[i:i + 400])

    def test_both_open_in_one_lightbox_in_order(self):
        """The comparison has to survive the click that magnifies it."""
        i = JS.index('$$("img.wiz-sample", col)')
        seg = " ".join(JS[i:i + 500].split())
        self.assertIn("RUN ${i + 1} OF ${imgs.length}", seg)
        self.assertIn("openLightbox(shots, i)", seg)


if __name__ == "__main__":
    unittest.main()
