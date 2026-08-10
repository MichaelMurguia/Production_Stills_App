"""Camera & composition language (user 2026-08-09).

A render told "High Camera Angle" ignored it: there was no camera field, and the
only composition the prompt carried was two terse tokens at the end. Camera is
now three structured axes (angle/tilt/lens) plus shot-size, each with an Art
Direction Bible default and a per-panel override, expanded by the app into an
authored directive placed high in the prompt and stated to outrank the
references' own framing.
"""
from __future__ import annotations

import inspect
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import generate, paths, store  # noqa: E402

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")

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


class CameraBlockTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-cam-"))
        _redirect_home(self.tmp)

    def tearDown(self):
        _restore_home()

    def test_panel_value_overrides_bible_default(self):
        store.save_camera_defaults({"camera_angle": "HIGH", "camera_lens": "NORMAL"})
        inherit = "\n".join(generate._camera_block({"purpose": "x"}))
        self.assertIn("HIGH ANGLE", inherit)          # inherited from the bible
        self.assertIn("NORMAL LENS", inherit)
        override = "\n".join(generate._camera_block({"camera_angle": "LOW"}))
        self.assertIn("LOW ANGLE", override)           # panel wins
        self.assertNotIn("HIGH ANGLE", override)
        self.assertIn("NORMAL LENS", override)         # unset axis still inherits

    def test_block_states_it_overrides_the_references(self):
        block = "\n".join(generate._camera_block({"camera_tilt": "DUTCH"}))
        self.assertIn("DUTCH ANGLE", block)
        self.assertIn("not the reference", block.lower())

    def test_empty_everywhere_emits_nothing(self):
        self.assertEqual(generate._camera_block({"purpose": "x"}), [])

    def test_every_enum_value_has_authored_phrasing(self):
        for field, allowed in store.CAMERA_FIELDS.items():
            for v in allowed:
                block = "\n".join(generate._camera_block({field: v}))
                if field == "camera_tilt" and v == "LEVEL":
                    continue  # LEVEL is intentionally silent
                self.assertTrue(block.strip(), f"{field}={v} produced no directive")


class CompilePlacementTests(unittest.TestCase):
    def test_camera_block_replaces_the_terse_tail(self):
        src = inspect.getsource(generate.compile_panel_prompt)
        self.assertIn("_camera_block(panel)", src)
        self.assertNotIn('f"SCALE: {panel', src, "the terse SCALE token must be gone")
        self.assertNotIn("COMPOSITION ROLE:", src)
        # the block is added right after PANEL PURPOSE, before DETAIL BUDGET
        self.assertLess(src.index("_camera_block(panel)"), src.index("DETAIL BUDGET"))
        self.assertGreater(src.index("_camera_block(panel)"), src.index("PANEL PURPOSE"))


class CameraDefaultsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-camdef-"))
        _redirect_home(self.tmp)

    def tearDown(self):
        _restore_home()

    def test_round_trip_and_normalisation(self):
        store.save_camera_defaults({"camera_angle": "high", "scale": "MEDIUM", "camera_tilt": ""})
        d = store.camera_defaults()
        self.assertEqual(d["camera_angle"], "HIGH")   # upper-cased
        self.assertEqual(d["scale"], "MEDIUM")
        self.assertNotIn("camera_tilt", d)            # empty dropped

    def test_unknown_value_is_refused(self):
        with self.assertRaises(ValueError):
            store.save_camera_defaults({"camera_angle": "SIDEWAYS"})


SPEC = {
    "specification_id": "CAM_V001",
    "status": "DRAFT",
    "panels": [
        {"id": "P01", "title": "HERO", "purpose": "the shop", "required_objects": ["x"]},
        {"id": "P02", "title": "", "purpose": "a neighbour"},
    ],
    "layout": {"panels": [{"id": "P01", "allocation_percent": 60},
                          {"id": "P02", "allocation_percent": 40}]},
    "evidence_ledger": [{"panel_id": "P01", "object": "x", "status": "PASS"}],
}


class AmendPanelCameraTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-camamend-"))
        _redirect_home(self.tmp)
        store.create_spec_from_dict(json.loads(json.dumps(SPEC)))

    def tearDown(self):
        _restore_home()

    def test_sets_fields_and_clears_on_empty(self):
        store.amend_panel_camera("CAM_V001", "P01", {"camera_angle": "LOW", "scale": "CLOSE"})
        p = next(x for x in store.get_spec("CAM_V001")["panels"] if x["id"] == "P01")
        self.assertEqual(p["camera_angle"], "LOW")
        self.assertEqual(p["scale"], "CLOSE")
        store.amend_panel_camera("CAM_V001", "P01", {"camera_angle": ""})  # clear
        p = next(x for x in store.get_spec("CAM_V001")["panels"] if x["id"] == "P01")
        self.assertNotIn("camera_angle", p)
        self.assertEqual(p["scale"], "CLOSE")         # untouched field stays

    def test_post_lock_restamps_and_journals(self):
        store.approve_spec("CAM_V001", lambda s: [])
        before = store.spec_lock_hash("CAM_V001")
        store.amend_panel_camera("CAM_V001", "P01", {"camera_angle": "HIGH"})
        self.assertNotEqual(before, store.spec_lock_hash("CAM_V001"))
        self.assertTrue(store.spec_locked("CAM_V001"))
        log = paths.APPROVAL_LOG.read_text(encoding="utf-8")
        self.assertIn("P01 camera amended post-lock", log)

    def test_approved_take_freezes_the_camera(self):
        d = paths.BOARDS_DIR / "CAM_V001"
        d.mkdir(parents=True, exist_ok=True)
        (d / "CAND-0001.json").write_text(json.dumps(
            {"candidate_id": "CAND-0001", "panel_id": "P01", "status": "APPROVED"}),
            encoding="utf-8")
        with self.assertRaises(PermissionError):
            store.amend_panel_camera("CAM_V001", "P01", {"camera_angle": "LOW"})
        store.amend_panel_camera("CAM_V001", "P02", {"camera_angle": "LOW"})  # neighbour ok

    def test_unknown_value_is_refused_before_mutation(self):
        with self.assertRaises(ValueError):
            store.amend_panel_camera("CAM_V001", "P01", {"camera_angle": "NOPE"})


class TheThreeSurfacesWireUp(unittest.TestCase):
    def test_js_defines_the_vocabulary_and_a_reusable_row(self):
        for c in ("CAMERA_ANGLES", "CAMERA_LENSES", "CAMERA_TILTS", "SHOT_SCALES",
                  "CAMERA_AXES", "function cameraSelect", "function cameraRow"):
            self.assertIn(c, JS)

    def test_sheet_editor_row_and_serialize(self):
        self.assertIn('cameraRow("pcam"', JS)
        self.assertIn('camera_angle: v("pcam-angle")', JS)
        self.assertIn('scale: v("pcam-scale")', JS)

    def test_bible_default_card_loads_and_saves(self):
        self.assertIn('id="cam-default-row"', HTML)
        self.assertIn('cameraRow("dcam"', JS)
        self.assertIn('/api/camera-defaults', JS)

    def test_workbench_inline_control_posts_and_is_frozen(self):
        self.assertIn('cameraRow("cam"', JS)
        self.assertIn("/panels/${p.id}/camera", JS)
        # the inline control is disabled when a take is approved (frozen)
        i = JS.index('data-f="cam-inline"')
        self.assertIn("frozen", JS[i:i + 400])


if __name__ == "__main__":
    unittest.main()
