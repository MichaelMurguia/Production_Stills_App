"""The sheet grammar (SHEET_SYSTEM_PLAN §12 + tech spec §7): the size
ladder with the R1 elastic/fixed ruling, the export gate's one list, caption
binding and staleness, /arrange's variant mapping and R4 strip, lookbooks —
all against a throwaway home so the real install is never touched."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import paths, sheet, store  # noqa: E402

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


def _write_spec(spec_id="SPEC-0001", panels=None):
    panels = panels if panels is not None else [
        {"id": "P1", "title": "Hero shot"}, {"id": "P2", "title": "Detail"}]
    spec = {"specification_id": spec_id, "subject": "BELT RIG EXTERIOR",
            "mode": "graybox", "board_type": "LOCATION",
            "setting": {"int_ext": "EXT", "location": "BELT RIG",
                        "time_of_day": "DAY"},
            "panels": panels,
            "layout": {"panels": [
                {"id": p["id"], "allocation_percent": 100 // max(1, len(panels))}
                for p in panels]}}
    (paths.SPECS_DIR / f"{spec_id}.json").write_text(
        json.dumps(spec), encoding="utf-8")
    return spec


def _write_candidate(spec_id, cand_id, panel_id, w=3840, h=2160,
                     status="APPROVED", notes=""):
    d = paths.BOARDS_DIR / spec_id
    d.mkdir(parents=True, exist_ok=True)
    rec = {"candidate_id": cand_id, "specification_id": spec_id,
           "panel_id": panel_id, "status": status, "width": w, "height": h,
           "model_notes": notes, "created_at": store.utcnow()}
    (d / f"{cand_id}.json").write_text(json.dumps(rec), encoding="utf-8")
    return rec


def _mk(medium="PRINT", blocks=(), size=None, source="CHOSEN"):
    """A bare sheet dict for the pure functions (recommend/readiness) —
    no storage round-trip."""
    return {"sheet_id": "SH-TEST", "archetype": "BOARD", "style": "INK",
            "medium": medium,
            "size": list(size or sheet.LADDERS[medium]["rungs"][0]),
            "size_source": source, "spine": False,
            "masthead": {"title": "", "subject": "", "binding": None},
            "blocks": list(blocks)}


def _block(btype, slots=None, frac=None):
    return {"block_id": f"B-{btype}", "type": btype,
            "frac": frac or {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0},
            "heading": None, "caption": None, "slots": slots or []}


class SheetHomeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-sheet-"))
        _redirect_home(self.tmp)

    def tearDown(self):
        _restore_home()


class RecommendTests(SheetHomeTest):
    """The worked-outcomes table in SHEET_SYSTEM_PLAN §6 is the oracle."""

    def test_print_hero_plus_principles_lands_12x8(self):
        # Elastic PRINCIPLES does not drag it to 24×16 (R1).
        s = _mk("PRINT", [_block("HERO"), _block("PRINCIPLES")])
        self.assertEqual(sheet.recommend(s), (12, 8))

    def test_print_middle_rung_via_ladder_mechanism(self):
        # No canon type has frac 0.01029 (worked-outcome row 2); the rung
        # is exercised with a test-only injected type — the canon set stays
        # closed at twelve.
        sheet.BLOCK_TYPES["TEST14"] = sheet.BlockDef(0, 0, 0.01029, False)
        try:
            s = _mk("PRINT", [_block("TEST14")])
            self.assertEqual(sheet.recommend(s), (18, 12))
        finally:
            del sheet.BLOCK_TYPES["TEST14"]

    def test_print_beats_scene_board_lands_36x24(self):
        s = _mk("PRINT", [_block("BEATS")])
        self.assertEqual(sheet.recommend(s), (36, 24))

    def test_print_ortho_never_below_36x24(self):
        s = _mk("PRINT", [_block("HERO"), _block("ORTHO")])
        self.assertEqual(sheet.recommend(s), (36, 24))

    def test_screen_hero_led_lands_1920(self):
        s = _mk("SCREEN", [_block("HERO")])
        self.assertEqual(sheet.recommend(s), (1920, 1080))

    def test_screen_cluster_and_beats_both_land_3840(self):
        # Two rungs, not three — the honest result of a fixed 24px floor
        # (R1: do not lower the floor to widen the spread).
        for btype in ("CLUSTER", "BEATS"):
            s = _mk("SCREEN", [_block(btype)])
            self.assertEqual(sheet.recommend(s), (3840, 2160), btype)

    def test_all_elastic_sheet_recommends_bottom_rung(self):
        s = _mk("PRINT", [_block("PALETTE"), _block("SPEC"),
                          _block("PRINCIPLES")])
        self.assertEqual(sheet.recommend(s), (12, 8))

    def test_elastic_type_renders_at_floor_never_under(self):
        b = _block("PRINCIPLES")
        # 0.00809 × 12in × 72 = 6.99pt — elastic grows to the 12pt floor.
        self.assertEqual(sheet.rendered_size(b, "PRINT", 12), 12.0)
        # At 36in it clears the floor on its own: 20.97pt.
        self.assertAlmostEqual(sheet.rendered_size(b, "PRINT", 36),
                               0.00809 * 36 * 72, places=2)
        # Fixed type never grows: HERO at 12in stays 12.7pt.
        self.assertAlmostEqual(
            sheet.rendered_size(_block("HERO"), "PRINT", 12),
            0.01471 * 12 * 72, places=2)

    def test_short_candidate_pushes_the_rung(self):
        # A filled slot short of pixels at 1920 forces the next rung that
        # both clears the floor and fits — here nothing bigger fits either,
        # so the ladder tops out (export will gate).
        _write_spec()
        _write_candidate("SPEC-0001", "CAND-0001", "P1", w=800, h=450)
        slot = {"slot_id": "S1", "spec_id": "SPEC-0001",
                "candidate_id": "CAND-0001",
                "frac": {"x": 0, "y": 0, "w": 1.0, "h": 1.0},
                "crop": {"x": 0, "y": 0, "w": 1.0, "h": 1.0, "rotate": 0.0}}
        s = _mk("SCREEN", [_block("HERO", slots=[slot])])
        self.assertEqual(sheet.recommend(s), (5120, 2880))

    def test_changing_size_mutates_no_frac(self):
        rec = sheet.create_sheet("ART_DIRECTION", "GALLERY", "PRINT")
        before = json.dumps([b["frac"] for b in rec["blocks"]]
                            + [s["frac"] for b in rec["blocks"]
                               for s in b["slots"]])
        rec["size"] = [36, 24]
        rec["size_source"] = "CHOSEN"
        after = sheet.save_sheet(rec)
        self.assertEqual(after["size"], [36, 24])
        now = json.dumps([b["frac"] for b in after["blocks"]]
                         + [s["frac"] for b in after["blocks"]
                            for s in b["slots"]])
        self.assertEqual(before, now)


class ReadinessTests(SheetHomeTest):
    def test_both_kinds_in_one_list(self):
        _write_spec()
        _write_candidate("SPEC-0001", "CAND-0001", "P1", w=200, h=100)
        short = {"slot_id": "S1", "spec_id": "SPEC-0001",
                 "candidate_id": "CAND-0001",
                 "frac": {"x": 0, "y": 0, "w": 1.0, "h": 1.0},
                 "crop": {"x": 0, "y": 0, "w": 1.0, "h": 1.0, "rotate": 0.0}}
        # BEATS type at 12in print sets at 5.7pt < 12pt → TYPE_FLOOR;
        # the 200px take is short of a print slot → SLOT_PIXELS.
        s = _mk("PRINT", [_block("BEATS", slots=[short])], size=(12, 8))
        r = sheet.readiness(s)
        kinds = sorted(e["kind"] for e in r["blocked"])
        self.assertEqual(kinds, ["SLOT_PIXELS", "TYPE_FLOOR"])
        self.assertFalse(r["ready"])

    def test_empty_slot_blocks_export_with_nothing(self):
        empty = {"slot_id": "S1", "spec_id": None, "candidate_id": None,
                 "frac": {"x": 0, "y": 0, "w": 1.0, "h": 1.0},
                 "crop": {"x": 0, "y": 0, "w": 1.0, "h": 1.0, "rotate": 0.0}}
        s = _mk("SCREEN", [_block("HERO", slots=[empty])],
                size=(1920, 1080))
        r = sheet.readiness(s)
        self.assertEqual(r["blocked"][0]["kind"], "SLOT_PIXELS")
        self.assertEqual(r["blocked"][0]["have"], [0, 0])

    def test_overcropping_is_kept_and_gates(self):
        # Cropping past the slot's pixel need is allowed and kept — the
        # slot turns short exactly as a small render does (plan §5).
        _write_spec()
        _write_candidate("SPEC-0001", "CAND-0001", "P1", w=3840, h=2160)
        slot = {"slot_id": "S1", "spec_id": "SPEC-0001",
                "candidate_id": "CAND-0001",
                "frac": {"x": 0, "y": 0, "w": 1.0, "h": 1.0},
                "crop": {"x": 0, "y": 0, "w": 1.0, "h": 1.0, "rotate": 0.0}}
        s = _mk("SCREEN", [_block("HERO", slots=[slot])], size=(3840, 2160))
        self.assertTrue(sheet.readiness(s)["ready"])
        slot["crop"] = {"x": 0.4, "y": 0.4, "w": 0.2, "h": 0.2, "rotate": 0.0}
        r = sheet.readiness(s)
        self.assertFalse(r["ready"])
        self.assertEqual(r["blocked"][0]["kind"], "SLOT_PIXELS")

    def test_ready_when_everything_clears(self):
        _write_spec()
        _write_candidate("SPEC-0001", "CAND-0001", "P1", w=3840, h=2160)
        slot = {"slot_id": "S1", "spec_id": "SPEC-0001",
                "candidate_id": "CAND-0001",
                "frac": {"x": 0, "y": 0, "w": 1.0, "h": 1.0},
                "crop": {"x": 0, "y": 0, "w": 1.0, "h": 1.0, "rotate": 0.0}}
        s = _mk("SCREEN", [_block("HERO", slots=[slot])], size=(1920, 1080))
        self.assertTrue(sheet.readiness(s)["ready"])
        self.assertEqual(sheet.readiness(s)["blocked"], [])


class CaptionBindingTests(SheetHomeTest):
    def _sheet_with_bound_caption(self):
        _write_spec()
        rec = sheet.create_sheet("LOCATION", "PLATE", "SCREEN")
        bid = rec["blocks"][0]["block_id"]
        rec = sheet.set_caption(rec["sheet_id"], bid, binding={
            "kind": "SPEC_FIELD", "id": "SPEC-0001", "field": "subject"})
        return rec, bid

    def test_bound_caption_reports_stale_after_source_change(self):
        rec, bid = self._sheet_with_bound_caption()
        cap = rec["blocks"][0]["caption"]
        self.assertEqual(cap["text"], "BELT RIG EXTERIOR")
        self.assertEqual(cap["state"], "BOUND")
        spec = store.get_spec("SPEC-0001")
        spec["subject"] = "BELT RIG INTERIOR"
        (paths.SPECS_DIR / "SPEC-0001.json").write_text(
            json.dumps(spec), encoding="utf-8")
        got = sheet.get_sheet(rec["sheet_id"])
        self.assertEqual(got["blocks"][0]["caption"]["state"], "STALE")

    def test_rebind_takes_the_new_line_and_never_touches_the_source(self):
        rec, bid = self._sheet_with_bound_caption()
        spec_path = paths.SPECS_DIR / "SPEC-0001.json"
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        spec["subject"] = "BELT RIG INTERIOR"
        spec_path.write_text(json.dumps(spec), encoding="utf-8")
        before = spec_path.read_bytes()
        got = sheet.resolve_caption(rec["sheet_id"], bid, "rebind")
        cap = got["blocks"][0]["caption"]
        self.assertEqual(cap["text"], "BELT RIG INTERIOR")
        self.assertEqual(cap["state"], "BOUND")
        self.assertEqual(spec_path.read_bytes(), before)

    def test_author_freezes_and_survives_further_drift(self):
        rec, bid = self._sheet_with_bound_caption()
        got = sheet.resolve_caption(rec["sheet_id"], bid, "author")
        self.assertEqual(got["blocks"][0]["caption"]["state"], "AUTHORED")
        spec_path = paths.SPECS_DIR / "SPEC-0001.json"
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        spec["subject"] = "SOMETHING ELSE ENTIRELY"
        spec_path.write_text(json.dumps(spec), encoding="utf-8")
        again = sheet.get_sheet(rec["sheet_id"])
        cap = again["blocks"][0]["caption"]
        self.assertEqual(cap["state"], "AUTHORED")
        self.assertEqual(cap["text"], "BELT RIG EXTERIOR")

    def test_palette_binding_preserves_swatch_order(self):
        refs = [{"id": f"REF-{i:04d}", "role": "COLOR_PALETTE",
                 "status": "APPROVED", "file": f"s{i}.png",
                 "notes": f"BELTMINER TECH · {name} · {hx} · bible"}
                for i, (name, hx) in enumerate(
                    [("Deep Sea", "#1B3A4B"), ("Rig Steel", "#5A6B7A"),
                     ("Signal Blue", "#3E7CB1")], start=1)]
        paths.REF_INDEX.write_text(json.dumps(refs), encoding="utf-8")
        text = sheet.resolve_binding(
            {"kind": "PALETTE_GROUP", "id": "BELTMINER TECH"})
        lines = text.splitlines()
        self.assertEqual(lines[0], "BELTMINER TECH")
        self.assertEqual([l.split()[0] for l in lines[1:]],
                         ["#1B3A4B", "#5A6B7A", "#3E7CB1"])

    def test_sheet_operations_never_write_specs_dir(self):
        _write_spec()
        snapshot = {p.name: p.read_bytes()
                    for p in paths.SPECS_DIR.glob("*.json")}
        rec = sheet.create_sheet("LOCATION", "PLATE", "SCREEN")
        bid = rec["blocks"][0]["block_id"]
        sheet.set_caption(rec["sheet_id"], bid, binding={
            "kind": "SPEC_FIELD", "id": "SPEC-0001", "field": "subject"})
        sheet.resolve_caption(rec["sheet_id"], bid, "author")
        sheet.add_block(rec["sheet_id"], "STRIP")
        sheet.delete_sheet(rec["sheet_id"])
        now = {p.name: p.read_bytes()
               for p in paths.SPECS_DIR.glob("*.json")}
        self.assertEqual(snapshot, now)


class ArrangeTests(SheetHomeTest):
    def _approve_all(self, spec_id="SPEC-0001", w=3840, h=2160):
        spec = store.get_spec(spec_id)
        for i, p in enumerate(spec["panels"], start=1):
            _write_candidate(spec_id, f"CAND-{i:04d}", p["id"], w=w, h=h)

    def _board_record(self, spec_id, variant):
        d = paths.BOARDS_DIR / spec_id
        d.mkdir(parents=True, exist_ok=True)
        (d / "BOARD-0001.json").write_text(json.dumps(
            {"candidate_id": "BOARD-0001", "layout_variant": variant}),
            encoding="utf-8")

    def test_arrange_twice_returns_same_sheet(self):
        _write_spec()
        self._approve_all()
        a = sheet.arrange_board("SPEC-0001")
        b = sheet.arrange_board("SPEC-0001")
        self.assertEqual(a["sheet_id"], b["sheet_id"])
        self.assertEqual(a["archetype"], "BOARD")
        self.assertEqual(a["style"], sheet.BOARD_STYLE)

    def test_default_variant_arranges_to_grid(self):
        _write_spec()
        self._approve_all()
        rec = sheet.arrange_board("SPEC-0001")
        self.assertEqual([b["type"] for b in rec["blocks"]], ["GRID"])
        placed = {s.get("panel_id"): s["candidate_id"]
                  for s in rec["blocks"][0]["slots"]}
        self.assertEqual(placed, {"P1": "CAND-0001", "P2": "CAND-0002"})

    def test_allocation_variant_arranges_to_cluster(self):
        _write_spec()
        self._approve_all()
        self._board_record("SPEC-0001", "allocation")
        rec = sheet.arrange_board("SPEC-0001")
        self.assertEqual([b["type"] for b in rec["blocks"]], ["CLUSTER"])

    def test_hero_variant_arranges_to_hero_plus_grid(self):
        _write_spec(panels=[{"id": "P1", "title": "Hero"},
                            {"id": "P2", "title": "B"},
                            {"id": "P3", "title": "C"}])
        self._approve_all()
        self._board_record("SPEC-0001", "hero:P1")
        rec = sheet.arrange_board("SPEC-0001")
        self.assertEqual([b["type"] for b in rec["blocks"]],
                         ["HERO", "GRID"])
        self.assertEqual(rec["blocks"][0]["slots"][0]["panel_id"], "P1")
        self.assertEqual(len(rec["blocks"][1]["slots"]), 2)

    def test_derived_takes_travel_as_a_strip_with_the_swap_note(self):
        _write_spec()
        self._approve_all()
        _write_candidate("SPEC-0001", "CAND-0090", "PALETTE",
                         w=3840, h=800)
        _write_candidate("SPEC-0001", "CAND-0091", "MATERIALS",
                         w=3840, h=800)
        rec = sheet.arrange_board("SPEC-0001")
        strip = rec["blocks"][-1]
        self.assertEqual(strip["type"], "STRIP")
        self.assertEqual(strip["caption"]["text"], sheet.DERIVED_SWAP_NOTE)
        carried = {s.get("panel_id") for s in strip["slots"]
                   if s.get("candidate_id")}
        self.assertEqual(carried, {"MATERIALS", "PALETTE"})

    def test_readiness_travels_too_small_maps_to_slot_pixels(self):
        # R5: stage-05's TOO_SMALL verdict surfaces as SLOT_PIXELS on the
        # arranged sheet — one vocabulary per surface.
        _write_spec(panels=[{"id": "P1", "title": "Hero"}])
        _write_candidate("SPEC-0001", "CAND-0001", "P1", w=640, h=360)
        rec = sheet.arrange_board("SPEC-0001")
        r = sheet.readiness(rec)
        self.assertFalse(r["ready"])
        self.assertTrue(all(e["kind"] == "SLOT_PIXELS"
                            for e in r["blocked"]))


class ModelTests(SheetHomeTest):
    def test_create_validates_vocabulary(self):
        with self.assertRaises(sheet.SheetError):
            sheet.create_sheet("BOARD", "PARCHMENT", "SCREEN")
        with self.assertRaises(sheet.SheetError):
            sheet.create_sheet("MOODBOARD", "INK", "SCREEN")
        with self.assertRaises(sheet.SheetError):
            sheet.create_sheet("BOARD", "INK", "WALL")

    def test_archetype_seeds_and_spine(self):
        art = sheet.create_sheet("ART_DIRECTION", "GALLERY", "PRINT")
        self.assertTrue(art["spine"])
        self.assertEqual([b["type"] for b in art["blocks"]],
                         ["CLUSTER"] * 7 + ["STRIP"])
        board = sheet.create_sheet("BOARD", "INK", "SCREEN")
        self.assertFalse(board["spine"])

    def test_slot_count_bounds_enforced(self):
        rec = sheet.create_sheet("BOARD", "INK", "SCREEN")
        bid = rec["blocks"][0]["block_id"]  # GRID, 4–12 slots
        for _ in range(8):
            rec = sheet.add_slot(rec["sheet_id"], bid)
        with self.assertRaises(sheet.SheetError):
            sheet.add_slot(rec["sheet_id"], bid)

    def test_every_save_bumps_rev(self):
        rec = sheet.create_sheet("BOARD", "INK", "SCREEN")
        r0 = rec["rev"]
        rec = sheet.add_block(rec["sheet_id"], "STRIP")
        self.assertEqual(rec["rev"], r0 + 1)

    def test_out_of_range_frac_rejected(self):
        rec = sheet.create_sheet("BOARD", "INK", "SCREEN")
        b = rec["blocks"][0]
        with self.assertRaises(sheet.SheetError):
            sheet.set_slot(rec["sheet_id"], b["block_id"],
                           b["slots"][0]["slot_id"],
                           {"frac": {"x": 0, "y": 0, "w": 1.4, "h": 1}})


class LookbookTests(SheetHomeTest):
    def test_lifecycle_and_reorder_guard(self):
        lb = sheet.create_lookbook("The Beltminers — pitch set")
        s1 = sheet.create_sheet("ART_DIRECTION", "GALLERY", "PRINT")
        s2 = sheet.create_sheet("SCENE_BOARD", "INK", "PRINT")
        sheet.lookbook_add_sheet(lb["lookbook_id"], s1["sheet_id"])
        lb = sheet.lookbook_add_sheet(lb["lookbook_id"], s2["sheet_id"])
        self.assertEqual(lb["sheets"], [s1["sheet_id"], s2["sheet_id"]])
        lb = sheet.lookbook_reorder(
            lb["lookbook_id"], [s2["sheet_id"], s1["sheet_id"]])
        self.assertEqual(lb["sheets"], [s2["sheet_id"], s1["sheet_id"]])
        with self.assertRaises(sheet.SheetError):
            sheet.lookbook_reorder(lb["lookbook_id"], [s1["sheet_id"]])

    def test_deleting_a_sheet_leaves_no_dangling_reference(self):
        lb = sheet.create_lookbook("Set")
        s1 = sheet.create_sheet("LOCATION", "PLATE", "SCREEN")
        sheet.lookbook_add_sheet(lb["lookbook_id"], s1["sheet_id"])
        sheet.delete_sheet(s1["sheet_id"])
        self.assertEqual(
            sheet.get_lookbook(lb["lookbook_id"])["sheets"], [])

    def test_candidates_tray_reports_placement(self):
        _write_spec()
        _write_candidate("SPEC-0001", "CAND-0001", "P1")
        _write_candidate("SPEC-0001", "CAND-0002", "P2",
                         status="CANDIDATE")
        rec = sheet.arrange_board("SPEC-0001")
        tray = sheet.lookbook_candidates()
        ids = {c["candidate_id"] for c in tray}
        self.assertIn("CAND-0001", ids)       # approved
        self.assertNotIn("CAND-0002", ids)    # unapproved never offered
        placed = next(c for c in tray if c["candidate_id"] == "CAND-0001")
        self.assertIn(rec["sheet_id"], placed["placed_in"])


class RenderTests(SheetHomeTest):
    """One renderer for preview and export (§10) — never upscale; sheets
    raise where boards letterbox (R2)."""

    def _png(self, spec_id, cand_id, w, h):
        from PIL import Image
        d = paths.BOARDS_DIR / spec_id
        d.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (w, h), (90, 84, 70)).save(d / f"{cand_id}.png")

    def _filled_sheet(self, cand_w, cand_h, size=(1920, 1080)):
        _write_spec()
        _write_candidate("SPEC-0001", "CAND-0001", "P1",
                         w=cand_w, h=cand_h)
        self._png("SPEC-0001", "CAND-0001", cand_w, cand_h)
        slot = {"slot_id": "S1", "spec_id": "SPEC-0001",
                "candidate_id": "CAND-0001", "label": "P1 — HERO",
                "frac": {"x": 0, "y": 0, "w": 1.0, "h": 1.0},
                "crop": {"x": 0, "y": 0, "w": 1.0, "h": 1.0, "rotate": 0.0}}
        return _mk("SCREEN", [_block("HERO", slots=[slot])], size=size)

    def test_render_raises_rather_than_letterboxing_on_a_short_slot(self):
        from app import sheet_render
        s = self._filled_sheet(640, 360, size=(3840, 2160))
        with self.assertRaises(sheet_render.RenderShortfall):
            sheet_render.render_sheet(s, 1.0)

    def test_board_path_letterboxes_and_says_so(self):
        from app import sheet_render
        s = self._filled_sheet(640, 360, size=(3840, 2160))
        warnings: list[str] = []
        img = sheet_render.render_sheet(s, 1.0, allow_letterbox=True,
                                        warnings=warnings)
        self.assertEqual(img.size, (3840, 2160))
        self.assertTrue(any("upscaling" in w for w in warnings))

    def test_preview_and_export_share_pixel_geometry(self):
        from app import sheet_render
        s = self._filled_sheet(1920, 1080)
        full = sheet_render.pixel_size(s, 1.0)
        quarter = sheet_render.pixel_size(s, 0.25)
        self.assertEqual(full, (1920, 1080))
        self.assertEqual(quarter, (480, 270))
        self.assertEqual(sheet_render.render_sheet(s, 0.25).size, quarter)

    def test_export_is_gated_then_lands_at_full_size(self):
        from app import sheet_render
        _write_spec()
        rec = sheet.create_sheet("BOARD", "INK", "SCREEN",
                                 title="THE BELTMINERS")
        # Fresh board sheet: empty slots block the export.
        with self.assertRaises(sheet.SheetError):
            sheet_render.export_sheet(rec["sheet_id"])
        # Fill every GRID slot with a real 4K take → ready → PNG lands.
        self._png("SPEC-0001", "CAND-0001", 3840, 2160)
        _write_candidate("SPEC-0001", "CAND-0001", "P1", w=3840, h=2160)
        for s in rec["blocks"][0]["slots"]:
            rec = sheet.set_slot(rec["sheet_id"],
                                 rec["blocks"][0]["block_id"], s["slot_id"],
                                 {"spec_id": "SPEC-0001",
                                  "candidate_id": "CAND-0001"})
        self.assertTrue(sheet.readiness(rec)["ready"])
        out = sheet_render.export_sheet(rec["sheet_id"])
        from PIL import Image
        with Image.open(out) as im:
            self.assertEqual(list(im.size), rec["size"])

    def test_print_export_renders_at_300dpi(self):
        from app import sheet_render
        s = _mk("PRINT", [_block("PRINCIPLES")], size=(12, 8))
        img = sheet_render.render_sheet(s, 1.0)
        self.assertEqual(img.size, (12 * 300, 8 * 300))

    def test_lookbook_pdf_carries_every_page(self):
        from app import sheet_render
        lb = sheet.create_lookbook("Pitch set")
        a = sheet.create_sheet("LOCATION", "PLATE", "SCREEN", title="A")
        # LOCATION seeds GRID (4 empty slots) — blocked; strip it to
        # elastic-only so the gate opens for the export test.
        a["blocks"] = [b for b in a["blocks"]
                       if sheet.BLOCK_TYPES[b["type"]].elastic]
        a = sheet.save_sheet(a)
        sheet.lookbook_add_sheet(lb["lookbook_id"], a["sheet_id"])
        out = sheet_render.export_lookbook(lb["lookbook_id"])
        self.assertTrue(out.exists())
        self.assertEqual(out.suffix, ".pdf")


class StageFiveDivisionTests(unittest.TestCase):
    """ba-4a: stage 05 judges readiness, the composer arranges. The one
    door is Arrange this board; the variant chips are gone; the Lookbook
    is a tool, never a stage."""

    JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")

    def test_arrange_door_beside_assemble(self):
        self.assertIn('id="asm-arrange"', self.JS)
        self.assertIn("Arrange this board", self.JS)
        i = self.JS.index('id="asm-arrange"')
        self.assertIn('id="asm-go"', self.JS[i:i + 800],
                      "the door stands beside Assemble, one head row")

    def test_variant_chips_left_stage_05(self):
        self.assertNotIn('label: "ALLOCATION"', self.JS)
        self.assertNotIn('data-f="variants"', self.JS)

    def test_lookbook_is_a_tool_not_a_stage(self):
        self.assertIn('data-view="lookbook"', self.HTML)
        i = self.JS.index("const STAGE_ORDER")
        self.assertNotIn("lookbook", self.JS[i:i + 200])
        i = self.JS.index('"tool-mode"')
        self.assertIn("lookbook", self.JS[i:i + 200],
                      "the band condenses while the Lookbook is open")

    def test_stage_03_copy_says_breakdown_not_sheet(self):
        # R7: one word, one meaning — the exact phrase is gone from every
        # user-facing surface.
        for src in (self.JS, self.HTML):
            self.assertNotIn("breakdown sheet", src.lower())


if __name__ == "__main__":
    unittest.main()
