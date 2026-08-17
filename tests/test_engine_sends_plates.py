"""Which engines put the reference IMAGES in front of the image model.

The application depends on reference plates (user 2026-08-16, holding a
likeness plate beside a render of a completely different man: "we need to
use a model that uses image reference — this application depends on it").
Two of the three built-in engines do it; one cannot, and the list read as
three interchangeable names.

- gemini   -> generate_content(contents=[prompt, *images])   plates
- openai   -> images.edit(image=files, prompt=...)           plates
- openai-chat -> GPT-5.6 SEES the photographs and calls an image tool that
  takes TEXT ONLY. The likeness survives exactly as well as the rewriter's
  prose describes it — and it wrote "the same recognizable man established
  by the approved likeness reference", which instructs the tool to match
  nothing and leaves it inventing a face from the surrounding adjectives.

Both halves are fixed here: the rewriter is told it is the only thing that
can see the plates and must describe them, and every surface that offers
an engine says which kind it is."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import generate  # noqa: E402

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
GEN = (ROOT / "app/generate.py").read_text(encoding="utf-8")


class TheEnginesDeclareIt(unittest.TestCase):
    def test_the_two_direct_engines_send_plates(self):
        self.assertTrue(generate.sends_plates("gemini"))
        self.assertTrue(generate.sends_plates("openai"))

    def test_the_chat_pipeline_does_not(self):
        self.assertFalse(generate.sends_plates("openai-chat"))

    def test_an_unknown_engine_is_assumed_to_send_them(self):
        """A custom engine speaks the OpenAI Images API, which means
        images.edit, which means the plates ride. Guessing the other way
        would put a false warning on every user-added engine."""
        self.assertTrue(generate.sends_plates("custom:whatever"))

    def test_the_claim_matches_the_render_code(self):
        """If a render path stops passing ref_paths, this flag becomes a
        lie — and it is a lie the user cannot see through."""
        gem = GEN[GEN.index("def _render_gemini"):GEN.index("def openai_size")]
        self.assertIn("contents.append(im)", gem)
        oai = GEN[GEN.index("def _render_openai("):GEN.index("def _render_custom")]
        self.assertIn("client.images.edit(", oai)
        self.assertIn("image=files", oai)
        chat = GEN[GEN.index("def _render_openai_chat"):GEN.index("# ------------------------------------------------------------- sample probes")]
        self.assertIn('"type": "input_image"', chat,
                      "the CHAT model does see them — it is the image tool that does not")
        self.assertIn('tool = {"type": "image_generation"', chat)


class TheRewriterIsToldItIsTheOnlyWitness(unittest.TestCase):
    def test_it_is_told_the_image_model_never_sees_the_plates(self):
        self.assertIn("YOU ARE THE ONLY THING THAT SEES THE ATTACHED REFERENCE IMAGES", GEN)
        self.assertIn("receives your text and nothing else", GEN)

    def test_it_is_told_what_a_likeness_description_must_contain(self):
        """Pointing at an attachment is what it used to do, and that is
        precisely the failure — so the rule names the features."""
        for w in ("hair COLOUR", "apparent age", "distinguishing mark"):
            self.assertIn(w, GEN, w)
        self.assertIn("Naming him and pointing at an attachment is not", GEN)

    def test_it_still_respects_role_scope(self):
        """A likeness reference tells you the face and nothing else — a
        rewriter that starts describing the costume from a face plate has
        broken the whole role system."""
        self.assertIn("Describe only what each role controls", GEN)


class EverySurfaceSaysWhichKind(unittest.TestCase):
    def test_the_engine_list_marks_the_blind_one(self):
        self.assertIn('sendsPlates(settings, v) ? "" : "  ·  NO REFERENCE IMAGES"', JS)

    def test_the_generate_step_warns_before_the_spend(self):
        self.assertIn('data-f="plates-warn"', JS)
        self.assertIn("THIS ENGINE NEVER SEES YOUR ${nPlates} REFERENCE PLATE", JS)

    def test_the_warning_only_fires_when_there_is_something_to_lose(self):
        i = JS.index("const blind = nPlates > 0")
        self.assertIn("!sendsPlates(appSettings, modelSel.value)", JS[i:i + 160])

    def test_the_warning_names_the_way_out(self):
        self.assertIn("PICK GEMINI OR GPT IMAGE 2 TO SEND THE IMAGES", JS)

    def test_the_client_reads_the_servers_declaration(self):
        """Not a hardcoded list in the JS — that is how the two drift."""
        self.assertIn("const m = (settings.provider_meta || {})[provider];", JS)
        self.assertNotIn('provider === "openai-chat"', JS)


if __name__ == "__main__":
    unittest.main()
