"""Correction intake (2026-08-13): a rejection becomes structure.

The GT40 failure: "side view … exploding in a fireball … canyon walls"
rode the next prompt as one prose bullet and mostly lost. Intake parses
the rejection into proposed deltas; the user applies them through the
journaled controlled-edit doors. The model proposes, the user promotes —
a misparse can only ever produce a bad proposal, never a bad spec.
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

from app import corrections, generate, mockflow, paths, store  # noqa: E402
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


REASON = ("Did not adhere to GRM hover jet reference. Would like a side "
          "view of the scene. Hoverjet should be exploding in a fireball. "
          "No neon signage.")

SPEC = {
    "specification_id": "INTAKE_V001",
    "status": "DRAFT",
    "mode": "CANON_EXTRACTION",
    "subject": "CANYON",
    "setting": {"int_ext": "EXT", "location": "CANYON"},
    "panels": [
        {"id": "P01", "title": "HERO", "purpose": "the getaway",
         "required_objects": ["gt40"], "composition_role": "hero"},
    ],
    "layout": {"panels": [{"id": "P01", "allocation_percent": 100}]},
    "evidence_ledger": [{"panel_id": "P01", "object": "gt40",
                         "status": "PASS"}],
}


def _write_rejection(spec_id="INTAKE_V001", cand="CAND-0001",
                     panel="P01", reason=REASON, status="REJECTED"):
    d = paths.BOARDS_DIR / spec_id
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{cand}.json").write_text(json.dumps(
        {"candidate_id": cand, "panel_id": panel, "status": status,
         "status_reason": reason}), encoding="utf-8")


class MockDeltasTests(unittest.TestCase):
    def test_the_gt40_reason_parses_into_structure(self):
        d = mockflow.correction_deltas(REASON, {})
        kinds = {(x["kind"], x.get("field", "")) for x in d["deltas"]}
        self.assertIn(("camera", "camera_orientation"), kinds)
        cam = next(x for x in d["deltas"] if x["kind"] == "camera")
        self.assertEqual(cam["value"], "SIDE")
        self.assertTrue(any(x["kind"] == "forbid" and "neon signage" in x["value"]
                            for x in d["deltas"]))
        self.assertTrue(any(x["kind"] == "require" and "exploding" in x["value"]
                            for x in d["deltas"]))


class CoerceDeltasTests(unittest.TestCase):
    def test_invalid_camera_and_unknown_kinds_drop(self):
        out = corrections._coerce_deltas({"deltas": [
            {"kind": "camera", "field": "camera_angle", "value": "SIDEWAYS"},
            {"kind": "camera", "field": "not_a_field", "value": "SIDE"},
            {"kind": "repaint", "value": "everything"},
            {"kind": "camera", "field": "camera_orientation", "value": "side"},
        ]}, {})
        self.assertEqual(out, [{"kind": "camera", "field": "camera_orientation",
                                "value": "SIDE", "applied": False}])

    def test_dedupes_against_the_panel_and_itself(self):
        panel = {"required_objects": ["The Jet"], "forbidden_objects": [],
                 "purpose": "a chase", "camera_orientation": "SIDE"}
        out = corrections._coerce_deltas({"deltas": [
            {"kind": "require", "value": "the jet"},          # already required
            {"kind": "camera", "field": "camera_orientation",
             "value": "SIDE"},                                 # already set
            {"kind": "forbid", "value": "neon"},
            {"kind": "forbid", "value": "NEON"},               # self-dupe
        ]}, panel)
        self.assertEqual([(d["kind"], d["value"]) for d in out],
                         [("forbid", "neon")])

    def test_volume_caps(self):
        out = corrections._coerce_deltas({"deltas": [
            {"kind": "require", "value": f"thing {i}"} for i in range(30)]}, {})
        self.assertEqual(len(out), corrections.MAX_DELTAS)


class ProposeApplyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-intake-"))
        _redirect_home(self.tmp)
        os.environ["SCREENBOARD_DEBUG_TOOLS"] = "1"
        generate.save_settings({"debug_mock": True})
        generate.save_style_bible(
            "# T\n\n## Rendering Language\n### Required\n- gouache\n")
        store.create_spec_from_dict(json.loads(json.dumps(SPEC)))
        store.approve_spec("INTAKE_V001", lambda s: [])
        _write_rejection()

    def tearDown(self):
        os.environ.pop("SCREENBOARD_DEBUG_TOOLS", None)
        _restore_home()

    def panel(self):
        return next(p for p in store.get_spec("INTAKE_V001")["panels"]
                    if p["id"] == "P01")

    def test_propose_stores_and_replaces_on_the_record(self):
        r1 = corrections.propose("INTAKE_V001", "CAND-0001", "mock")
        self.assertTrue(r1["deltas"])
        rec = generate.get_candidate("INTAKE_V001", "CAND-0001")
        self.assertEqual(rec["correction_intake"]["provider"], "mock")
        r2 = corrections.propose("INTAKE_V001", "CAND-0001", "mock")
        self.assertEqual(len(r2["deltas"]), len(r1["deltas"]),
                         "re-propose replaces, it does not accumulate")

    def test_only_a_reasoned_rejection_can_intake(self):
        _write_rejection(cand="CAND-0002", status="APPROVED")
        with self.assertRaises(generate.GenerationError):
            corrections.propose("INTAKE_V001", "CAND-0002", "mock")
        _write_rejection(cand="CAND-0003", reason="")
        with self.assertRaises(generate.GenerationError):
            corrections.propose("INTAKE_V001", "CAND-0003", "mock")

    def test_apply_routes_through_the_controlled_doors(self):
        r = corrections.propose("INTAKE_V001", "CAND-0001", "mock")
        before = store.spec_lock_hash("INTAKE_V001")
        corrections.apply("INTAKE_V001", "CAND-0001",
                          list(range(len(r["deltas"]))))
        p = self.panel()
        self.assertEqual(p["camera_orientation"], "SIDE")
        self.assertTrue(any("neon signage" in x
                            for x in p["forbidden_objects"]))
        self.assertTrue(any("exploding" in x.lower()
                            for x in p["required_objects"]))
        self.assertNotEqual(before, store.spec_lock_hash("INTAKE_V001"),
                            "the lock re-stamps")
        log = paths.APPROVAL_LOG.read_text(encoding="utf-8")
        self.assertIn("structured from CAND-0001's rejection", log)
        rec = generate.get_candidate("INTAKE_V001", "CAND-0001")
        self.assertTrue(all(d["applied"]
                            for d in rec["correction_intake"]["deltas"]))

    def test_reapply_never_duplicates(self):
        r = corrections.propose("INTAKE_V001", "CAND-0001", "mock")
        idx = list(range(len(r["deltas"])))
        corrections.apply("INTAKE_V001", "CAND-0001", idx)
        n_req = len(self.panel()["required_objects"])
        corrections.apply("INTAKE_V001", "CAND-0001", idx)
        self.assertEqual(len(self.panel()["required_objects"]), n_req)

    def test_approved_take_freezes_the_apply(self):
        corrections.propose("INTAKE_V001", "CAND-0001", "mock")
        _write_rejection(cand="CAND-0009", status="APPROVED", reason="")
        with self.assertRaises(PermissionError):
            corrections.apply("INTAKE_V001", "CAND-0001", [0])

    def test_end_to_end_the_correction_reaches_the_prompt_twice(self):
        """Applied structure AND the verbatim carry coexist: the camera
        block says SIDE VIEW, and the rejection text rides head + tail."""
        r = corrections.propose("INTAKE_V001", "CAND-0001", "mock")
        corrections.apply("INTAKE_V001", "CAND-0001",
                          list(range(len(r["deltas"]))))
        spec, panel, refs = generate._resolve_generation_inputs(
            "INTAKE_V001", "P01", [])
        prompt = generate.compile_panel_prompt(spec, panel, refs)
        self.assertIn("SIDE VIEW", prompt)
        self.assertIn("DIRECTOR'S CORRECTIONS", prompt)
        self.assertEqual(prompt.count("Would like a side view"), 2,
                         "verbatim at the head and the tail echo")


class IntakeApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-intakeapi-"))
        _redirect_home(self.tmp)
        os.environ["SCREENBOARD_DEBUG_TOOLS"] = "1"
        generate.save_settings({"debug_mock": True,
                                "narrative_provider": "openai"})
        store.create_spec_from_dict(json.loads(json.dumps(SPEC)))
        store.approve_spec("INTAKE_V001", lambda s: [])
        _write_rejection()
        self.client = TestClient(appmain.app)

    def tearDown(self):
        os.environ.pop("SCREENBOARD_DEBUG_TOOLS", None)
        _restore_home()

    def test_propose_apply_dismiss_round_trip(self):
        base = "/api/specs/INTAKE_V001/candidates/CAND-0001/correction-intake"
        r = self.client.post(base, json={"provider": "mock"})
        self.assertEqual(r.status_code, 200, r.text)
        deltas = r.json()["deltas"]
        self.assertTrue(deltas)
        a = self.client.post(base + "/apply", json={"indices": [0]})
        self.assertEqual(a.status_code, 200, a.text)
        self.assertEqual(a.json()["applied"], 1)
        d = self.client.post(base + "/dismiss")
        self.assertEqual(d.status_code, 200)
        rec = generate.get_candidate("INTAKE_V001", "CAND-0001")
        self.assertTrue(rec["correction_intake"]["dismissed"])

    def test_bad_targets_state_themselves(self):
        base = "/api/specs/INTAKE_V001/candidates/CAND-0404/correction-intake"
        self.assertEqual(self.client.post(base, json={"provider": "mock"})
                         .status_code, 404)
        self.assertEqual(self.client.post(
            "/api/specs/INTAKE_V001/candidates/CAND-0001/correction-intake",
            json={"provider": "palantir"}).status_code, 422)


class UiWiringTests(unittest.TestCase):
    JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")

    def test_reject_triggers_a_proposal_and_the_rail_shows_it(self):
        self.assertIn("proposeCorrections(specId, c.candidate_id, refresh)",
                      self.JS)
        self.assertIn("PROPOSED STRUCTURE — FROM THIS REJECTION", self.JS)
        self.assertIn("data-apply-intake", self.JS)
        self.assertIn("data-dismiss-intake", self.JS)

    def test_the_acts_stay_text_acts(self):
        i = self.JS.index("data-apply-intake=")
        self.assertIn("text-act", self.JS[i - 200:i + 200],
                      "apply/dismiss are ghosts — Generate keeps primacy")


if __name__ == "__main__":
    unittest.main()
