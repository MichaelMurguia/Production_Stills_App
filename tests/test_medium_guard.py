"""Regression (user-hit 2026-08-06): a bake-off sample rendered
photo-real past an attached BOARD_RENDERING_STYLE anchor. The sample
prompt had invited it ("as it would appear in the film"); both the
sample probe and the panel compiler now restate the board medium as
non-negotiable whenever the board anchor rides — and stay silent when
it doesn't (a photoreal Bible is a legitimate choice)."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import generate  # noqa: E402
from tests.test_app_api import _redirect_home, _restore_home  # noqa: E402

GUARD = "THE MEDIUM IS NOT NEGOTIABLE"

SPEC = {"specification_id": "SPEC-T", "subject": "test", "panels": [],
        "mode": "CANON_EXTRACTION", "forbidden_elements": []}
PANEL = {"id": "P1", "description": "the crash site at noon",
         "required_objects": [], "forbidden_objects": []}


def _ref(role):
    return {"id": "REF-X", "role": role, "notes": "", "controls": [],
            "does_not_control": []}


class MediumGuardTests(unittest.TestCase):
    def setUp(self):
        # The compiler needs a saved Bible for its style context.
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-guard-"))
        _redirect_home(self.tmp)
        self.addCleanup(_restore_home)
        generate.save_style_bible(
            "# T\n\n## Rendering Language\n### Required\n- gouache\n"
            "### Avoid\n- chrome\n")

    def test_panel_prompt_guards_when_board_anchor_rides(self):
        p = generate.compile_panel_prompt(SPEC, PANEL,
                                          [_ref("BOARD_RENDERING_STYLE")])
        self.assertIn(GUARD, p)
        self.assertIn("A photographic result is a failed render", p)

    def test_panel_prompt_silent_without_board_anchor(self):
        p = generate.compile_panel_prompt(SPEC, PANEL, [_ref("COLOR_PALETTE")])
        self.assertNotIn(GUARD, p,
                         "a photoreal Bible is a legitimate choice — the "
                         "guard exists only to honor an attached board anchor")

    def test_bible_instructions_fence_rendering_language(self):
        """The drafting instructions fence Rendering Language to a single
        panel's paint; board architecture is sent to Production Board
        Presentation (user-hit 2026-08-06: a draft wrote the whole board
        grammar into the globally-injected section)."""
        from app import wizard
        text = wizard._bible_instructions({})
        self.assertIn("SECTION FENCE", text)
        self.assertIn("SINGLE panel's artwork only", text)
        self.assertIn("take only its paint from it", text)

    def test_sample_probe_prompt_demands_board_artwork(self):
        import os
        os.environ["SCREENBOARD_DEBUG_TOOLS"] = "1"
        self.addCleanup(os.environ.pop, "SCREENBOARD_DEBUG_TOOLS", None)
        from fastapi.testclient import TestClient

        import app.main as appmain
        client = TestClient(appmain.app)
        client.post("/api/projects", json={"name": "Guard Demo"})
        client.post("/api/settings", json={"debug_mock": True})
        client.put("/api/style-bible", json={"text":
            "# T\n\n## Rendering Language\n### Required\n- gouache\n### Avoid\n- chrome\n"})
        # board anchor present -> the guard must ride the sample prompt
        client.post("/api/references/swatch", json={"hex": "#8A4B2E", "approve": True})
        from app import wizard
        r = client.post("/api/references", files={"file": ("b.png",
            wizard.render_swatch_png("#111111"), "image/png")},
            data={"role": "BOARD_RENDERING_STYLE"})
        self.assertEqual(r.status_code, 200, r.text)
        client.post(f"/api/references/{r.json()['id']}/status",
                    json={"status": "APPROVED"})

        captured = {}
        real = generate.mockflow.render

        def spy(prompt, refs, size, aspect, out):
            captured["prompt"] = prompt
            return real(prompt, refs, size, aspect, out)

        generate.mockflow.render = spy
        self.addCleanup(setattr, generate.mockflow, "render", real)
        r = client.post("/api/wizard/samples/mock", json={"subject": "CRASH SITE"})
        self.assertEqual(r.status_code, 200, r.text)
        p = captured["prompt"]
        self.assertIn("ONE PANEL OF A PRODUCTION DESIGN BOARD", p)
        self.assertIn("NEVER a photograph or a film still", p)
        self.assertIn(GUARD, p)
        self.assertNotIn("as it would appear in the film", p,
                         "the photoreal invitation must stay dead")


if __name__ == "__main__":
    unittest.main()
