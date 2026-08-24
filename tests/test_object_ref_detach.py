"""A required object can be ruled NOT covered by a reference group
(user 2026-08-16: "I have reference for 'airlock hatch behind Sal' and its
green but the reference is wrong so I want to delete it").

The app decides which plates cover an object by matching wording against
the group's name, and that match cannot read grammar: "airlock hatch
behind Sal" names Sal because Sal is IN the phrase, though the object is
an airlock and Sal is only where it sits. A possessive, a preposition and
a subject all look alike to a matcher — so the answer is not a cleverer
guess, it is being overrulable.

"Delete" here must not mean deleting the reference. The plate is correct
canon and is correctly attached to other objects; only THIS pairing is
wrong."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")


class TheOverruleIsStoredOnThePanel(unittest.TestCase):
    def setUp(self):
        from app import paths
        self.tmp = tempfile.TemporaryDirectory()
        home = Path(self.tmp.name)
        self._old = {k: getattr(paths, k)
                     for k in ("SPECS_DIR", "SPEC_LOCKS", "APPROVAL_LOG")}
        (home / "specs").mkdir(parents=True)
        (home / "state").mkdir(parents=True)
        paths.SPECS_DIR = home / "specs"
        paths.SPEC_LOCKS = home / "specs" / "locks.json"
        paths.APPROVAL_LOG = home / "state" / "approval_log.md"
        (paths.SPECS_DIR / "T_V001.json").write_text(json.dumps({
            "specification_id": "T_V001", "subject": "t",
            "mode": "CANON_EXTRACTION", "board_type": "SCENE",
            "panels": [{"id": "P01", "title": "t", "purpose": "p",
                        "required_objects": ["airlock hatch behind Sal"]}],
            "evidence_ledger": [],
        }), encoding="utf-8")

    def tearDown(self):
        from app import paths
        for k, v in self._old.items():
            setattr(paths, k, v)
        self.tmp.cleanup()

    def test_excluding_and_restoring(self):
        from app import store
        r = store.amend_object_refs("T_V001", "P01", "airlock hatch behind Sal",
                                    exclude=["SAL CRAFT", "SAL'S CRYO-CHAMBER"])
        self.assertEqual(r["excluded"], ["SAL CRAFT", "SAL'S CRYO-CHAMBER"])
        spec = store.get_spec("T_V001")
        self.assertEqual(spec["panels"][0]["ref_exclusions"],
                         {"airlock hatch behind Sal": ["SAL CRAFT", "SAL'S CRYO-CHAMBER"]})
        r2 = store.amend_object_refs("T_V001", "P01", "airlock hatch behind Sal",
                                     include=["SAL CRAFT"])
        self.assertEqual(r2["excluded"], ["SAL'S CRYO-CHAMBER"])

    def test_the_key_disappears_when_nothing_is_excluded(self):
        """A panel carrying an empty table would drift the spec hash for no
        reason and read as a rule where there is none."""
        from app import store
        store.amend_object_refs("T_V001", "P01", "airlock hatch behind Sal",
                                exclude=["SAL CRAFT"])
        store.amend_object_refs("T_V001", "P01", "airlock hatch behind Sal",
                                include=["SAL CRAFT"])
        self.assertNotIn("ref_exclusions", store.get_spec("T_V001")["panels"][0])

    def test_it_names_the_object_it_cannot_find(self):
        from app import store
        with self.assertRaises(ValueError):
            store.amend_object_refs("T_V001", "P01", "   ", exclude=["X"])

    def test_it_is_journaled(self):
        from app import store, paths
        store.amend_object_refs("T_V001", "P01", "airlock hatch behind Sal",
                                exclude=["SAL CRAFT"])
        log = paths.APPROVAL_LOG.read_text(encoding="utf-8")
        self.assertIn("ruled NOT its reference", log)
        self.assertIn("never a take already rendered", log)


class TheUiOffersIt(unittest.TestCase):
    def test_the_matcher_honours_the_overrule(self):
        self.assertIn("const excluded = obj => (p.ref_exclusions || {})[String(obj)] || [];", JS)
        self.assertIn("!excluded(obj).includes(name) && namesPhrase(obj, name)", JS)

    def test_the_plate_viewer_carries_the_verb(self):
        self.assertIn('data-f="vr-detach"', JS)
        # TRIAGE §1 (ruled 2026-08-18): `Remove reference` read as a
        # library deletion, and the row's own note said the tooltip
        # carried the whole burden — a verb that needs a tooltip to not
        # be misread is the wrong verb.
        self.assertIn(">Not this object's reference</button>", JS)

    def test_the_copy_says_the_plates_are_not_deleted(self):
        """The verb is "Remove reference" (user-chosen 2026-08-16), which
        reads like a library deletion — so the tooltip carries the whole
        weight of saying it is not one. It unpairs THIS object; the plates
        survive and stay attached to every other object that names them."""
        i = JS.index('data-f="vr-detach"')
        seg = JS[i:i + 600]
        self.assertIn("FROM THIS OBJECT only", seg)
        self.assertIn("plates themselves are untouched", seg)
        self.assertIn("stay in the library", seg)
        self.assertIn("every other object that names them", seg)

    def test_it_posts_the_exclusion(self):
        self.assertIn("/object-refs`", JS)
        self.assertIn("exclude: gs.map(g => g.name)", JS)

    def test_choosing_a_group_deliberately_undoes_the_overrule(self):
        """Otherwise the tile stays + REF while its plate rides — the two
        halves disagreeing again, which is the whole family of bug this
        day was spent on."""
        self.assertIn("if (excluded(obj).includes(g.name))", JS)
        self.assertIn("include: [g.name]", JS)

    def test_the_endpoint_exists_and_has_a_caller(self):
        self.assertIn('@app.post("/api/specs/{spec_id}/panels/{panel_id}/object-refs")', MAIN)
        self.assertGreaterEqual(JS.count("/object-refs`"), 2)


class AMisfiledReferenceCanBeRescoped(unittest.TestCase):
    """User-caught 2026-08-24: "I cant edit and change Dark Ship refference
    type."

    A tester filed a spaceship as CHARACTER_LIKENESS — the role the
    walkthrough named — and nothing in the app could take it back. The
    PATCH endpoint existed and NO SCREEN HAD EVER CALLED IT, so the role
    chosen at intake was permanent for the life of the reference; and for
    an APPROVED reference the store refused the change outright, offering
    "reject it first" as the remedy. Rejecting is a judgement on the
    IMAGE, and a misfiled image was never the problem."""

    def setUp(self):
        import json as _json
        import tempfile
        from app import paths
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self._old = (paths.REF_INDEX, paths.APPROVAL_LOG)
        paths.REF_INDEX = d / "references.json"
        paths.APPROVAL_LOG = d / "approval_log.md"
        paths.REF_INDEX.write_text(_json.dumps([{
            "id": "REF-0046", "role": "CHARACTER_LIKENESS — DARK SHIP",
            "status": "APPROVED", "controls": ["face", "hair"],
            "does_not_control": [], "file": "x.png"}]), encoding="utf-8")

    def tearDown(self):
        from app import paths
        paths.REF_INDEX, paths.APPROVAL_LOG = self._old
        self.tmp.cleanup()

    def rec(self):
        import json as _json
        from app import paths
        return _json.loads(paths.REF_INDEX.read_text(encoding="utf-8"))[0]

    def test_the_reported_case(self):
        from app import store
        store.rescope_reference("REF-0046", "VEHICLE_GEOMETRY — DARK SHIP")
        self.assertTrue(self.rec()["role"].startswith("VEHICLE_GEOMETRY"))

    def test_the_approval_survives(self):
        """Re-scoping is not re-judging. Forcing a reject to fix a filing
        error would throw away the review the image already passed."""
        from app import store
        store.rescope_reference("REF-0046", "VEHICLE_GEOMETRY — DARK SHIP")
        self.assertEqual(self.rec()["status"], "APPROVED")

    def test_jurisdiction_travels_with_the_role(self):
        """"face, hair" is meaningless once this is a vehicle."""
        from app import store
        store.rescope_reference("REF-0046", "VEHICLE_GEOMETRY — DARK SHIP",
                                ["hull geometry"], ["colour"])
        r = self.rec()
        self.assertEqual(r["controls"], ["hull geometry"])
        self.assertEqual(r["does_not_control"], ["colour"])

    def test_omitting_jurisdiction_leaves_it_alone(self):
        """A role correction must not silently wipe facets the user set."""
        from app import store
        store.rescope_reference("REF-0046", "VEHICLE_GEOMETRY — DARK SHIP")
        self.assertEqual(self.rec()["controls"], ["face", "hair"])

    def test_it_is_journaled(self):
        """A canon anchor changing jurisdiction is a production fact: every
        render made under the old role meant something different by it."""
        from app import paths, store
        store.rescope_reference("REF-0046", "VEHICLE_GEOMETRY — DARK SHIP")
        log = paths.APPROVAL_LOG.read_text(encoding="utf-8")
        self.assertIn("RE-SCOPED", log)
        self.assertIn("CHARACTER_LIKENESS", log)
        self.assertIn("VEHICLE_GEOMETRY", log)

    def test_an_empty_role_is_refused(self):
        from app import store
        with self.assertRaises(ValueError):
            store.rescope_reference("REF-0046", "   ")

    def test_an_unknown_reference_is_a_keyerror(self):
        from app import store
        with self.assertRaises(KeyError):
            store.rescope_reference("REF-9999", "VEHICLE_GEOMETRY")

    def test_the_generic_patch_still_refuses(self):
        """The lock was right for a silent field edit — this adds a stated
        act beside it, it does not remove the guard."""
        from app import store
        with self.assertRaises(PermissionError):
            store.update_reference("REF-0046", {"role": "VEHICLE_GEOMETRY"})

    def test_the_library_offers_it(self):
        js = (Path(__file__).resolve().parents[1] / "app/static/app.js").read_text(encoding="utf-8")
        self.assertIn('rs.textContent = "Edit"', js)
        self.assertIn("/rescope`", js)

    def test_the_route_exists(self):
        main = (Path(__file__).resolve().parents[1] / "app/main.py").read_text(encoding="utf-8")
        self.assertIn('@app.post("/api/references/{ref_id}/rescope")', main)


class TheFlightRecorderCannotBeTheThingThatFails(unittest.TestCase):
    """A body that is not valid UTF-8 raised UnicodeDecodeError inside the
    activity middleware — which caught JSONDecodeError only — so the client
    got a 500 from the recorder before any route saw the request. Found
    2026-08-24 when a Windows shell sent a cp1252 em-dash."""

    def test_it_catches_a_decode_error_too(self):
        main = (Path(__file__).resolve().parents[1] / "app/main.py").read_text(encoding="utf-8")
        i = main.index("body_summary = _redact_secrets(json.loads(raw))")
        self.assertIn("UnicodeDecodeError", main[i:i + 200])

    def test_a_non_utf8_body_does_not_500(self):
        import tempfile
        from fastapi.testclient import TestClient
        from app import paths
        from app.main import app
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        old = paths.HOME
        paths.HOME = Path(tmp.name)
        try:
            r = TestClient(app).post("/api/references/NOPE/rescope",
                                     content=b'{"role":"A ' + bytes([0x97]) + b' B"}',
                                     headers={"Content-Type": "application/json"})
            self.assertLess(r.status_code, 500, r.text)
        finally:
            paths.HOME = old


if __name__ == "__main__":
    unittest.main()
