"""Scene composition check (2026-08-13).

Motivated by CANYON_GRM_GT40_GETAWAY: a hero GT40 rendered small at an
arbitrary angle — nothing ever asked whether the prompt's framing served
the scene's action. The check is advisory, pre-render, text-only; its
verdict shape is coerced server-side and its alignment is computed, never
read from the model.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app import composition, generate, mockflow, paths, store  # noqa: E402
import app.main as appmain  # noqa: E402

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


class CoerceVerdictTests(unittest.TestCase):
    def test_unknown_axis_and_severity_clamp(self):
        v = composition._coerce_verdict({"findings": [
            {"axis": "VIBES", "severity": "FATAL", "note": "x"}]})
        self.assertEqual(v["findings"][0]["axis"], "COMPOSITION")
        self.assertEqual(v["findings"][0]["severity"], "WARN")

    def test_alignment_is_computed_never_read(self):
        v = composition._coerce_verdict({
            "alignment": "OK",  # the model's claim is ignored
            "findings": [{"axis": "ANGLE", "severity": "WARN", "note": "x"}]})
        self.assertEqual(v["alignment"], "WARN")
        clean = composition._coerce_verdict({
            "alignment": "WARN",
            "findings": [{"axis": "ANGLE", "severity": "NOTE", "note": "x"}]})
        self.assertEqual(clean["alignment"], "OK")

    def test_noteless_findings_drop_and_volume_caps(self):
        v = composition._coerce_verdict({"findings":
            [{"axis": "ANGLE", "severity": "NOTE", "note": ""}]
            + [{"axis": "ANGLE", "severity": "NOTE", "note": f"n{i}"}
               for i in range(20)]})
        self.assertLessEqual(len(v["findings"]), composition.MAX_FINDINGS)
        self.assertTrue(all(f["note"] for f in v["findings"]))

    def test_suggested_camera_is_validated_per_axis(self):
        v = composition._coerce_verdict({
            "findings": [{"axis": "SUBJECT_PROMINENCE", "severity": "WARN",
                          "note": "small"}],
            "suggested_camera": {"scale": "FULL_BODY",       # legacy → WIDE
                                 "camera_orientation": "side",  # normalises
                                 "camera_angle": "SIDEWAYS",    # invalid → drop
                                 "camera_lens": "NOT_A_LENS"}})  # invalid → drop
        self.assertEqual(v["suggested_camera"],
                         {"scale": "WIDE", "camera_orientation": "SIDE"})

    def test_no_warn_means_no_camera_and_no_amendment(self):
        v = composition._coerce_verdict({
            "findings": [{"axis": "ANGLE", "severity": "NOTE", "note": "fine"}],
            "suggested_camera": {"scale": "CLOSE"},
            "purpose_amendment": "do not keep this"})
        self.assertIsNone(v["suggested_camera"])
        self.assertEqual(v["purpose_amendment"], "")

    def test_vocabulary_block_carries_every_axis(self):
        vocab = composition._camera_vocabulary()
        for field in store.CAMERA_FIELDS:
            self.assertIn(field, vocab)
        self.assertIn("SIDE", vocab)
        self.assertIn("focal length", vocab)


class MockVerdictTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-comp-"))
        _redirect_home(self.tmp)

    def tearDown(self):
        _restore_home()

    def test_hero_at_extreme_wide_earns_the_gt40_warning(self):
        d = mockflow.composition_check(
            {}, {"composition_role": "hero", "scale": "EXTREME_WIDE"},
            "prompt", {"matched": True})
        warns = [f for f in d["findings"] if f["severity"] == "WARN"]
        self.assertEqual(warns[0]["axis"], "SUBJECT_PROMINENCE")
        self.assertTrue(warns[0]["note"].startswith("MOCK VERDICT"))
        self.assertEqual(d["suggested_camera"], {"scale": "WIDE"})

    def test_support_panel_is_clean_and_stamped(self):
        d = mockflow.composition_check(
            {}, {"composition_role": "support", "scale": "MEDIUM"},
            "prompt", {"matched": True})
        self.assertTrue(all(f["severity"] == "NOTE" for f in d["findings"]))
        self.assertTrue(all(f["note"].startswith("MOCK VERDICT")
                            for f in d["findings"]))

    def test_unanchored_scene_is_stated(self):
        d = mockflow.composition_check(
            {}, {"composition_role": "support"}, "prompt", {"matched": False})
        self.assertTrue(any("not located" in f["note"]
                            for f in d["findings"]))


SPEC = {
    "specification_id": "COMP_V001",
    "status": "DRAFT",
    "mode": "CANON_EXTRACTION",
    "subject": "CANYON",
    "setting": {"int_ext": "EXT", "location": "CANYON"},
    "scene": "A chase along the canyon rim.",
    "panels": [
        {"id": "P01", "title": "HERO", "purpose": "the getaway",
         "required_objects": ["gt40"], "composition_role": "hero",
         "scale": "EXTREME_WIDE"},
    ],
    "layout": {"panels": [{"id": "P01", "allocation_percent": 100}]},
    "evidence_ledger": [{"panel_id": "P01", "object": "gt40",
                         "status": "PASS"}],
}


class CompositionApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-compapi-"))
        _redirect_home(self.tmp)
        os.environ["SCREENBOARD_DEBUG_TOOLS"] = "1"
        generate.save_settings({"debug_mock": True})
        # The compiler needs a saved Bible for its style context.
        generate.save_style_bible(
            "# T\n\n## Rendering Language\n### Required\n- gouache\n")
        store.create_spec_from_dict(json.loads(json.dumps(SPEC)))
        store.approve_spec("COMP_V001", lambda s: [])
        self.client = TestClient(appmain.app)

    def tearDown(self):
        os.environ.pop("SCREENBOARD_DEBUG_TOOLS", None)
        _restore_home()

    def post(self, panel="P01", **body):
        return self.client.post(
            f"/api/specs/COMP_V001/panels/{panel}/composition-check",
            json={"ref_ids": [], "provider": "mock", **body})

    def test_mock_check_end_to_end(self):
        r = self.post()
        self.assertEqual(r.status_code, 200, r.text)
        v = r.json()
        self.assertEqual(v["alignment"], "WARN")   # hero at EXTREME_WIDE
        self.assertEqual(v["suggested_camera"], {"scale": "WIDE"})
        self.assertEqual(v["provider"], "mock")
        self.assertEqual(len(v["spec_hash"]), 8)
        # no screenplay uploaded in this throwaway home — stated, not fatal
        self.assertFalse(v["anchor"]["matched"])
        self.assertTrue(any("not located" in f["note"]
                            for f in v["findings"]))

    def test_unknown_provider_is_422(self):
        r = self.post(provider="palantir")
        self.assertEqual(r.status_code, 422)

    def test_missing_panel_is_404(self):
        r = self.post(panel="P99")
        self.assertEqual(r.status_code, 404)

    def test_unlocked_spec_is_422(self):
        spec2 = json.loads(json.dumps(SPEC))
        spec2["specification_id"] = "COMP_V002"
        store.create_spec_from_dict(spec2)
        r = self.client.post(
            "/api/specs/COMP_V002/panels/P01/composition-check",
            json={"ref_ids": [], "provider": "mock"})
        self.assertEqual(r.status_code, 422)


class UiWiringTests(unittest.TestCase):
    JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")

    def test_check_sits_with_the_free_actions_and_stays_text_act(self):
        i = self.JS.index('data-f="compcheck"')
        self.assertIn('class="text-act"', self.JS[i - 120:i + 40],
                      "never amber — Generate keeps the card's primacy")
        self.assertIn("/composition-check", self.JS)

    def test_apply_goes_through_the_existing_camera_editor(self):
        i = self.JS.index("data-f=comp-apply")
        block = self.JS[i:i + 1400]
        self.assertIn("camOpen.click()", block,
                      "the suggestion prefills the one existing editor; "
                      "the user still saves through the journaled POST")


if __name__ == "__main__":
    unittest.main()
