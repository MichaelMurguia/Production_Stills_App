"""Four design languages must not share one palette.

User, 2026-08-22, on the first real swatch run: "when I generated swatches
I have 4 swatches of VERY similar colors. Something is not right about
that. Diagnose."

They were right, and the fault was upstream of the swatch pass. Measured
on that production's own proposals:

  * Of 27 colours, 23 had a near-twin (ΔE < 9) in a DIFFERENT design
    language. Not one swatch in the set was more than ΔE 11.7 from a
    colour belonging to another faction.
  * Every language had the same six-slot recipe — a near-black, a cream,
    a neutral grey, a blue-grey, a brown and a rust red.
  * Two heroes, Skunkworks #39463D and Soviet #596156, sat ΔE 12.1 apart:
    on a board, one faction.

The cause was in the BIBLE. Its Design Language section spec asked for
keywords, a one-line design language and bullets — and nothing about
colour. Three of that production's four languages named no colour at all,
and the swatch pass is told "a colour the bible cannot support is not
proposed", so it fell back to the bible's global colour language and
returned one palette wearing four labels.

Three layers, because prompting alone cannot be verified:
  1. every design language must state a `Color identity` of its own
  2. the swatch pass is told the languages must be distinguishable
  3. the RESULT is measured, and says so when it repeats itself
"""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

WIZ = (ROOT / "app" / "wizard.py").read_text(encoding="utf-8")
JS = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
HTML = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")

# The reporting production's real proposals, by design language.
REAL = {
    "Skunkworks Engineering": ["#39463D", "#D8D4C5", "#687074", "#735843",
                               "#8A4B2E", "#777267", "#B9B2A0"],
    "CIA Covert Network": ["#D6CEB7", "#777A73", "#9A7B55", "#8A3D32",
                           "#2A2B29", "#53636A", "#4B453E"],
    "Soviet Counterintelligence": ["#596156", "#C8C0AA", "#7A302B", "#515C60",
                                   "#804B35", "#282D2D"],
    "Oxcart Technology": ["#15191A", "#59433A", "#9A7041", "#A7AAA4",
                          "#747A7A", "#A23E32", "#444647"],
}
HEROES = {"Skunkworks Engineering": "#39463D", "CIA Covert Network": "#D6CEB7",
          "Soviet Counterintelligence": "#596156", "Oxcart Technology": "#15191A"}


def real_groups():
    return [{"language": lang,
             "swatches": [{"name": h, "hex": h, "hero": HEROES[lang] == h}
                          for h in hexes]}
            for lang, hexes in REAL.items()]


class DistanceIsPerceptualNotArithmetic(unittest.TestCase):

    def test_identical_colours_are_zero_apart(self):
        from app import wizard
        self.assertEqual(wizard.delta_e("#8A4B2E", "#8A4B2E"), 0.0)

    def test_a_real_contrast_is_far(self):
        from app import wizard
        self.assertGreater(wizard.delta_e("#D8D4C5", "#15191A"), 60)

    def test_lab_not_rgb(self):
        """Two greys and two reds are not equally far apart just because
        their bytes are. Byte distance would call these equal."""
        from app import wizard
        grey = wizard.delta_e("#777777", "#8A8A8A")
        red = wizard.delta_e("#770000", "#8A0000")
        self.assertNotAlmostEqual(grey, red, places=0)


class TheCheckCatchesTheReportedRun(unittest.TestCase):
    """The regression test for a bug that reached the user: the exact
    proposals they were looking at must trip it."""

    def found(self):
        from app import wizard
        return wizard.swatch_collisions(real_groups())

    def test_it_reports_the_set_as_one_palette(self):
        overlap = [c for c in self.found() if c["kind"] == "OVERLAP"]
        self.assertTrue(overlap, "23 of 27 colours repeated and nothing said so")
        self.assertGreaterEqual(overlap[0]["delta"], 60)
        self.assertIn("one palette", overlap[0]["text"])

    def test_it_names_the_two_factions_that_read_alike(self):
        heroes = [c for c in self.found() if c["kind"] == "HERO"]
        self.assertTrue(heroes)
        pair = {heroes[0]["a"], heroes[0]["b"]}
        self.assertEqual(pair, {"Skunkworks Engineering",
                                "Soviet Counterintelligence"})

    def test_the_measure_is_set_level_not_pairwise(self):
        """A pairwise test found NOTHING on this data — the repetition was
        spread evenly across all four languages, so no single pair crossed
        the threshold while a viewer saw it at a glance."""
        from app import wizard
        gs = real_groups()
        worst = 0.0
        for i, ga in enumerate(gs):
            for gb in gs[i + 1:]:
                twins = sum(1 for a in ga["swatches"]
                            if any(wizard.delta_e(a["hex"], b["hex"])
                                   < wizard.TWIN_DELTA for b in gb["swatches"]))
                worst = max(worst, twins / len(ga["swatches"]))
        self.assertLess(worst, wizard.OVERLAP_SHARE,
                        "if a pair DID cross it, this test no longer proves "
                        "why the measure has to be set-level")

    def test_four_distinct_palettes_trip_nothing(self):
        """The check must not simply always complain."""
        from app import wizard
        gs = [{"language": n, "swatches": [{"name": h, "hex": h, "hero": i == 0}
                                           for i, h in enumerate(hexes)]}
              for n, hexes in (
                  ("Reds", ["#B03A2E", "#E6B0AA", "#7B241C"]),
                  ("Blues", ["#1F618D", "#AED6F1", "#154360"]),
                  ("Greens", ["#1E8449", "#A9DFBF", "#145A32"]),
              )]
        self.assertEqual(wizard.swatch_collisions(gs), [])


class TheBibleGivesEachLanguageItsOwnColour(unittest.TestCase):

    def test_the_section_spec_asks_for_a_colour_identity(self):
        self.assertIn("**Color identity:**", WIZ)
        self.assertIn("WHAT SEPARATES IT FROM THE OTHER WORLDS", WIZ)

    def test_the_drafter_is_told_the_worlds_must_differ(self):
        self.assertIn("EACH DESIGN LANGUAGE OWNS ITS OWN COLOR", WIZ)
        self.assertIn("make the worlds DIFFER", WIZ)
        self.assertIn("not a palette", WIZ)

    def test_the_swatch_pass_is_told_the_same(self):
        self.assertIn("THE DESIGN LANGUAGES MUST NOT SHARE A PALETTE", WIZ)
        self.assertIn("six-slot recipe", WIZ,
                      "name the failure mode, not just the rule")

    def test_the_progress_surface_reports_which_languages_lack_one(self):
        """The diagnostic the user never had: a language with no colour of
        its own is visible while the bible is being written."""
        self.assertIn("NO COLOUR OF ITS OWN", JS)
        self.assertIn("languages own a colour identity", JS)

    def test_a_section_is_read_to_its_own_end(self):
        """A fixed-width slice ran into the NEXT section, so a language
        with no colour line borrowed its neighbour's and the count read 4
        of 4 when it was 3."""
        i = JS.index("this.identity[l] =")
        seg = JS[max(0, i - 500):i + 120]
        self.assertIn('md.indexOf("\\n## ", i + 3)', seg)


class TheVerdictReachesTheScreen(unittest.TestCase):

    def test_the_route_returns_what_was_measured(self):
        self.assertIn('"collisions": swatch_collisions(parsed)', WIZ)

    def test_the_strip_shows_it(self):
        self.assertIn("sw-collide", JS)
        self.assertIn("r.collisions || []", JS)

    def test_it_reports_rather_than_blocks(self):
        """Amber marks what blocks. This does not block — the proposals
        are still there to approve — so it must not wear amber."""
        css = (ROOT / "app" / "static" / "styles.css").read_text(encoding="utf-8")
        block = css.split(".sw-collide {")[1].split("/* A saved bible")[0]
        self.assertNotIn("--accent", block)
        self.assertIn("--bad-line", block)

    def test_the_verdict_can_be_dismissed(self):
        """It reports rather than blocks, so a verdict the user has read
        and decided about must be closable — otherwise it is noise sitting
        over the work it is about (user, 2026-08-22)."""
        self.assertIn("sw-collide-x", JS)
        self.assertIn('$("[data-f=collide]", strip)?.remove()', JS)
        css = (ROOT / "app" / "static" / "styles.css").read_text(encoding="utf-8")
        self.assertIn(".sw-collide-x", css)

    def test_dismissing_leaves_the_proposals_alone(self):
        """Only the block is removed — nothing about the swatches, their
        approval state or the strip beneath it."""
        i = JS.index('cx.onclick')
        self.assertNotIn("api(", JS[i:i + 200])


class ASwatchCanBeRenamedWhereItIsRepainted(unittest.TestCase):
    """User, 2026-08-22: "when you choose to recolor a swatch you need to
    be able to edit its name as well." A repaint is exactly the moment a
    name stops being true — OXIDE BLOOM repainted blue is worse than an
    unnamed colour."""

    def home(self):
        import tempfile
        from app import paths
        paths.HOME = pathlib.Path(tempfile.mkdtemp(prefix="rn-"))
        paths.set_project("")
        paths.ensure_dirs()

    def swatch(self, notes, source):
        from app import store, wizard
        return store.add_reference("s.png", wizard.render_swatch_png("#8A4B2E"),
                                   role="COLOR_PALETTE", controls=[],
                                   does_not_control=[], notes=notes,
                                   source=source)

    def notes_of(self, ref_id):
        from app import store
        return store.get_reference(ref_id)["notes"]

    def test_a_proposal_keeps_its_language(self):
        """Proposals note LANGUAGE · NAME · HEX · CITE. A rename that
        counted from the left would overwrite the design language."""
        self.home()
        from app import wizard
        r = self.swatch("Skunkworks Engineering · OXIDE BLOOM · #8A4B2E · rust",
                        "swatch-proposal")
        wizard.recolor_swatch(r["id"], "#123456", None, "COLD STEEL")
        self.assertEqual(self.notes_of(r["id"]),
                         "Skunkworks Engineering · COLD STEEL · #123456 · rust")

    def test_a_manual_swatch_leads_with_its_name(self):
        """Manual swatches note NAME · HEX · CITE — one segment fewer, so
        the name's index differs and is read off `source`, not counted."""
        self.home()
        from app import wizard
        r = self.swatch("BLOOD · #AA0000", "swatch-manual")
        wizard.recolor_swatch(r["id"], "#00AA00", None, "MOSS")
        self.assertEqual(self.notes_of(r["id"]), "MOSS · #00AA00")

    def test_a_proposal_that_came_back_nameless_gains_one(self):
        self.home()
        from app import wizard
        r = self.swatch("CIA Covert Network · #010203", "swatch-proposal")
        wizard.recolor_swatch(r["id"], "#040506", None, "INK")
        self.assertEqual(self.notes_of(r["id"]),
                         "CIA Covert Network · INK · #040506")

    def test_omitting_the_name_leaves_it_alone(self):
        """Recolouring without renaming must not blank the name."""
        self.home()
        from app import wizard
        r = self.swatch("Oxcart Technology · JP-7 AMBER · #9A7041 · fuel",
                        "swatch-proposal")
        wizard.recolor_swatch(r["id"], "#111111")
        self.assertIn("JP-7 AMBER", self.notes_of(r["id"]))

    def test_the_verb_no_longer_says_only_repaint(self):
        self.assertNotIn('confirmLabel: "Repaint swatch"', JS)
        self.assertIn('confirmLabel: "Save swatch"', JS)

    def test_the_form_offers_the_name_first(self):
        i = JS.index("const swatchFields = ")
        seg = JS[i:i + 1100]
        self.assertLess(seg.index('name: "name"'), seg.index('name: "hex"'))

    def test_adding_and_editing_state_a_swatch_the_same_way(self):
        """They were two forms. The inline one could not state a value-key
        pair at all, and it left an `input[type=color]` painted #8a4b2e in
        the palette column — a filled rust square that read as a swatch
        nobody had added (user-hit 2026-08-22: "I am still getting the odd
        Oxide color swatch that shows up when there are no other color
        swatches")."""
        self.assertEqual(JS.count("const swatchFields = "), 1)
        self.assertEqual(JS.count("fields: swatchFields("), 2)
        for gone in ("sw-color", "sw-hex", "sw-name-in", "sw-hex-in"):
            self.assertNotIn(gone, HTML, gone)
            self.assertNotIn(gone, JS, gone)
        # nothing coloured is left on the page that is not a swatch
        i = HTML.index('<div class="swatch-add')
        self.assertNotIn("<input", HTML[i:HTML.index("</div>", i)])

    def test_a_hand_added_swatch_can_state_its_value_key_pair(self):
        """What the shared form gains it: the endpoint always took
        `pair_hex`, and only the editing half ever sent one."""
        i = JS.index('title: "Add a palette swatch"')
        self.assertIn("pair_hex:", JS[i:i + 1100])


if __name__ == "__main__":
    unittest.main()
