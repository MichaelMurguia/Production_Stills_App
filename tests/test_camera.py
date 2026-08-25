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
        store.save_camera_defaults({"camera_angle": "HIGH", "camera_lens": "50MM"})
        inherit = "\n".join(generate._camera_block({"purpose": "x"}))
        self.assertIn("HIGH ANGLE", inherit)          # inherited from the bible
        self.assertIn("50mm LENS", inherit)
        override = "\n".join(generate._camera_block({"camera_angle": "LOW"}))
        self.assertIn("LOW ANGLE", override)           # panel wins
        self.assertNotIn("HIGH ANGLE", override)
        self.assertIn("50mm LENS", override)           # unset axis still inherits

    def test_block_states_it_overrides_the_references(self):
        block = "\n".join(generate._camera_block({"camera_tilt": "DUTCH"}))
        self.assertIn("DUTCH ANGLE", block)
        self.assertIn("not the reference", block.lower())

    def test_baseline_speaks_when_nothing_is_set(self):
        """A production starts from CAMERA_BASELINE (Eye level · 24mm ·
        Level · Wide, user 2026-08-10) — a panel with no camera of its own
        inherits it, so the block always states the house grammar."""
        block = "\n".join(generate._camera_block({"purpose": "x"}))
        self.assertIn("WIDE SHOT", block)
        self.assertIn("24mm LENS", block)

    def test_every_enum_value_has_authored_phrasing(self):
        for field, allowed in store.CAMERA_FIELDS.items():
            if hasattr(allowed, "match"):
                continue  # the lens is a focal length — covered below
            for v in allowed:
                block = "\n".join(generate._camera_block({field: v}))
                if field == "camera_tilt" and v == "LEVEL":
                    continue  # LEVEL is intentionally silent
                self.assertTrue(block.strip(), f"{field}={v} produced no directive")

    def test_legacy_autofill_scale_still_speaks(self):
        # Regression (2026-08-12 review): pre-enum autofill drafts persisted
        # FULL_BODY / DETAIL verbatim; the shot axis silently vanished from
        # the prompt. They migrate onto the canon enum at resolve time.
        full = "\n".join(generate._camera_block({"scale": "FULL_BODY"}))
        self.assertIn("WIDE SHOT", full)
        detail = "\n".join(generate._camera_block({"scale": "DETAIL"}))
        self.assertIn("EXTREME CLOSE-UP", detail)

    def test_unrecognized_value_falls_back_to_the_default(self):
        # A hand-edited or imported value never silences an axis — it
        # degrades to the production default, the house grammar.
        store.save_camera_defaults({"camera_angle": "HIGH"})
        block = "\n".join(generate._camera_block({"camera_angle": "SIDEWAYS"}))
        self.assertIn("HIGH ANGLE", block)

    def test_the_ui_migrates_legacy_scale_words(self):
        # The sheet editor showed the inherit option for a stored FULL_BODY;
        # the select now shows (and a save persists) the migrated value.
        self.assertIn("_LEGACY_SCALE", JS)
        self.assertIn('FULL_BODY: "WIDE"', JS)
        self.assertIn('DETAIL: "EXTREME_CLOSE"', JS)

    def test_orientation_has_no_baseline_and_stays_silent_unset(self):
        """Orientation is subject-relative — a house default would fight
        every panel's references. Nothing set = no VIEW directive."""
        self.assertNotIn("camera_orientation", store.CAMERA_BASELINE)
        block = "\n".join(generate._camera_block({"purpose": "x"}))
        self.assertNotIn("VIEW —", block)

    def test_side_view_is_now_expressible_as_structure(self):
        """The CANYON_GRM_GT40_GETAWAY failure: 'side view' could only ride
        as prose. It is an axis now, and it outranks the references."""
        block = "\n".join(generate._camera_block({"camera_orientation": "SIDE"}))
        self.assertIn("SIDE VIEW", block)
        self.assertIn("true profile", block)
        self.assertIn("not the reference", block.lower())

    def test_orientation_emits_between_lens_and_angle(self):
        block = "\n".join(generate._camera_block(
            {"camera_orientation": "REAR", "camera_angle": "LOW"}))
        self.assertLess(block.index("24mm LENS"), block.index("REAR VIEW"))
        self.assertLess(block.index("REAR VIEW"), block.index("LOW ANGLE"))

    def test_every_focal_length_has_authored_phrasing(self):
        """Presets, the legacy names, and custom lengths all resolve to a
        directive whose character derives from the millimetres."""
        for v in ("18MM", "24MM", "35MM", "50MM", "85MM", "135MM",
                  "8MM", "200MM", "WIDE", "NORMAL", "TELEPHOTO"):
            line = generate._lens_phrasing(v)
            self.assertTrue(line, f"lens {v} produced no directive")
            self.assertIn("LENS", line)


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
        # An empty value clears the stored override; the read then shows
        # the baseline through it (camera_defaults is baseline-merged).
        self.assertEqual(d["camera_tilt"], store.CAMERA_BASELINE["camera_tilt"])
        self.assertEqual(d["camera_lens"], store.CAMERA_BASELINE["camera_lens"])

    def test_unknown_value_is_refused(self):
        with self.assertRaises(ValueError):
            store.save_camera_defaults({"camera_angle": "SIDEWAYS"})

    def test_orientation_round_trips_and_clears_to_nothing(self):
        """Unlike the baselined axes, a cleared orientation shows NO value
        through the merge — unset is a legitimate stored state."""
        store.save_camera_defaults({"camera_orientation": "side"})
        self.assertEqual(store.camera_defaults()["camera_orientation"], "SIDE")
        store.save_camera_defaults({"camera_orientation": ""})
        self.assertNotIn("camera_orientation", store.camera_defaults())


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

    def test_orientation_sets_and_clears_like_any_axis(self):
        store.amend_panel_camera("CAM_V001", "P01",
                                 {"camera_orientation": "THREE_QUARTER_REAR"})
        p = next(x for x in store.get_spec("CAM_V001")["panels"] if x["id"] == "P01")
        self.assertEqual(p["camera_orientation"], "THREE_QUARTER_REAR")
        store.amend_panel_camera("CAM_V001", "P01", {"camera_orientation": ""})
        p = next(x for x in store.get_spec("CAM_V001")["panels"] if x["id"] == "P01")
        self.assertNotIn("camera_orientation", p)


class TheThreeSurfacesWireUp(unittest.TestCase):
    def test_js_defines_the_vocabulary_and_a_reusable_row(self):
        for c in ("CAMERA_ANGLES", "CAMERA_ORIENTATIONS", "CAMERA_LENSES",
                  "CAMERA_TILTS", "SHOT_SCALES",
                  "CAMERA_AXES", "function cameraSelect", "function cameraRow"):
            self.assertIn(c, JS)

    def test_orientation_wires_through_all_three_surfaces(self):
        """The axis rides CAMERA_AXES, so every surface renders it; the
        reader returns it; the defaults card keeps it clearable via the
        per-axis unset label (that card renders with no blank option)."""
        self.assertIn('["SIDE", "Side — profile"]', JS)
        self.assertIn('key: "camera_orientation"', JS)
        self.assertIn('unset: "— free —"', JS)
        self.assertIn('camera_orientation: val("orient")', JS)

    def test_sheet_editor_row_and_serialize(self):
        self.assertIn('cameraRow("pcam"', JS)
        # the row serialises through readCameraFields, which resolves a Custom
        # focal length to e.g. "28MM" (a plain v("pcam-lens") would read "CUSTOM")
        self.assertIn('readCameraFields("pcam", row)', JS)

    def test_lens_is_focal_lengths_with_a_custom_option(self):
        self.assertIn('["24MM", "24mm"]', JS)
        self.assertIn('["135MM", "135mm"]', JS)
        self.assertIn("Custom", JS)
        self.assertIn("-lens-mm", JS)          # the custom focal-length input

    def test_shot_list_has_the_new_types(self):
        for s in ('["AERIAL", "Aerial"]', '["MACRO", "Macro"]', '["MICRO", "Micro"]'):
            self.assertIn(s, JS)

    def test_the_production_camera_card_is_gone(self):
        """A4 (2026-08-25), superseding the 2026-08-16 ruling that put
        this card beside the cinematography anchor.

        That ruling was right about the problem and reached for the
        weaker fix. Two inputs that can contradict each other were placed
        where you can see them together — but the card was still a
        production-wide `Eye level · 24mm · Level · Wide` that nobody
        chose, riding every prompt as a directive. Seeing a contradiction
        is not the same as not having one, and under a grammar asking for
        50–100mm at f/1.4–2.8 a deep-focus wide is a straight
        contradiction. It defeated the cinematography axis for two days.

        The grammar carries framings now. There is one camera authority."""
        self.assertNotIn('id="cam-default"', HTML)
        self.assertNotIn('id="cam-default-row"', HTML)
        self.assertNotIn('cameraRow("dcam"', JS)

    def test_the_look_never_dictates_the_lens(self):
        """User 2026-08-16: "a cinematographer will pick any lens to get
        the shot." The catalogue is light behaviour only, and the picker
        writes one field — its own."""
        j = JS.index('title: "Cinematography"')
        seg = JS[j:j + 900]
        self.assertIn("whatever lens gets the shot", seg)
        # The grammar SANCTIONS framings; it does not dictate one. A
        # panel picks from that family or overrules it with its own
        # camera, which is the same rule stated in optics rather than
        # in a separate card (A4, 2026-08-25).
        self.assertIn("overrules it with its own", seg)
        # and the picker writes ONE field — its own
        i = JS.index("const bindPicker =")
        self.assertNotIn("cam-", JS[i:i + 1500],
                         "the look never reaches into the camera row")

    def test_the_default_survives_as_a_silent_fallback(self):
        """A4.2 — the values still exist and still answer the breakdown's
        "— production default —". They are simply no longer presented as a
        choice anyone made. The endpoint stays too: removing a control is
        a separate decision from removing an endpoint, and a production
        that set values before today keeps rendering with them."""
        from app import store
        self.assertTrue(store.camera_defaults())
        self.assertIn('@app.get("/api/camera-defaults")',
                      (ROOT / "app/main.py").read_text(encoding="utf-8"))
        self.assertNotIn("loadCameraDefault", JS)

    def test_workbench_states_then_opens_then_freezes(self):
        """Canon pass R7 (2026-08-10, mock au-wb-camera): the workbench
        judges takes, so the camera in force is ONE Courier line with the
        verb beside it; the selects open on ask; an approved take freezes
        the act with the condition in its title."""
        self.assertIn('cameraRow("cam"', JS)
        self.assertIn("/panels/${p.id}/camera", JS)
        # The verb now lives on the step's shared right edge (§1.4), which
        # is authored before the body — so the window starts at the step.
        i = JS.index('n: "03", id: "camera"')
        block = JS[i:i + 3200]
        self.assertIn("cam-stated", block)
        self.assertIn("Change camera", block)
        self.assertIn("PRODUCTION DEFAULT", block)
        self.assertIn("THIS PANEL", block)
        self.assertIn("Frozen by an approved take", block)
        self.assertIn('NEVER "CUSTOM"', block)
        self.assertIn("Save camera", block)


class ChangeCameraIsActuallyWired(unittest.TestCase):
    """User-hit 2026-08-22: "on the panels screen there is the option to
    Change camera but if you click it, nothing happens."

    Nothing was bound to it. `seqStep` renders `verbs` inside the step's
    HEAD and `body` beneath, so the button is a SIBLING of `.cam-inline`
    and never a descendant — and both lookups scoped the query to
    `.cam-inline`. `$()` returned null, the `if (openBtn ...)` guard
    swallowed it, and the button sat there inert. The guard is what made
    it silent: a missing element read as a disabled one."""

    def test_the_button_is_rendered_in_the_steps_verbs(self):
        i = JS.index('step({ n: "03", id: "camera"')
        seg = JS[i:i + 900]
        v, b = seg.index("verbs:"), seg.index("body:")
        self.assertLess(v, b, "verbs come first in the step call")
        self.assertIn('data-f="cam-open"', seg[v:b])
        self.assertNotIn('data-f="cam-open"', seg[b:])

    def test_the_editor_it_opens_is_inside_the_body(self):
        """The two halves of the same step — which is exactly why one
        scope cannot find both."""
        i = JS.index('step({ n: "03", id: "camera"')
        seg = JS[i:i + 1800]
        b = seg.index("body:")
        self.assertIn('data-f="cam-editor"', seg[b:])
        self.assertIn('data-f="cam-inline"', seg[b:])

    def test_both_lookups_scope_to_the_card(self):
        """Not to cam-inline. The second one silently disabled the
        composition check's Apply suggested camera as well, because
        canApply needs the button it could not find."""
        self.assertEqual(JS.count('$("[data-f=cam-open]", card)'), 2)
        self.assertNotIn('$("[data-f=cam-open]", camInline)', JS)
        self.assertNotIn('$("[data-f=cam-open]", camInl)', JS)

    def test_opening_reveals_the_editor_and_hides_the_stated_line(self):
        i = JS.index('const openBtn = $("[data-f=cam-open]", card);')
        seg = JS[i:i + 400]
        self.assertIn('editor.classList.remove("hidden")', seg)
        self.assertIn('$(".cam-stated", camInline).classList.add("hidden")', seg)

    def test_a_frozen_panel_still_refuses_to_open(self):
        """The disabled state is the one case where nothing happening is
        correct, and it states why in its title."""
        i = JS.index('data-f="cam-open"')
        seg = JS[i:i + 400]
        self.assertIn("frozen ?", seg)
        self.assertIn("Frozen by an approved take", seg)
        self.assertIn("if (openBtn && !openBtn.disabled)", JS)


class TheInheritLabelNamesTheRightPlace(unittest.TestCase):
    """User-caught 2026-08-16: "what does 'from Bible' mean on per panel
    camera settings?" It meant nothing — the default is the production's
    camera grammar in data/camera_defaults.json, set on the Cinematography
    anchor in Production Design. The Art Direction Bible has never held
    it, so the label sent anyone who read it to the wrong document."""

    def test_the_blank_option_names_what_it_inherits(self):
        # only the comment explaining the rename may still say it
        self.assertEqual(JS.lower().count("from bible"), 2)
        self.assertNotIn('"— from bible —"', JS)
        self.assertIn('"— production default —"', JS)

    def test_the_step_meta_says_it_too(self):
        self.assertIn('"— PRODUCTION DEFAULT"', JS)
        self.assertIn("VIEW NOT FIXED — PRODUCTION DEFAULT", JS)

    def test_the_default_really_does_live_there(self):
        st = (ROOT / "app/store.py").read_text(encoding="utf-8")
        i = st.index("def camera_defaults()")
        self.assertIn("CAMERA_DEFAULTS", st[i:i + 500])
        self.assertNotIn("BIBLE", st[i:i + 500])


if __name__ == "__main__":
    unittest.main()
