"""The consolidation strip — the surface that ends the two-breakdown state
(user 2026-08-16: "I still have 2 CANYON_GRM breakdowns. Lets
consolodate.").

A migration surface, not a permanent control: it exists only while a unit
is still split, and states the whole consequence before the act rather
than reporting it afterwards."""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")


def fn(name: str) -> str:
    i = JS.index(f"function {name}(")
    return JS[i:JS.index(chr(10) + "}" + chr(10), i)]


class TheStrip(unittest.TestCase):
    def setUp(self):
        self.body = fn("renderConsolidateStrips")

    def test_it_has_a_home_above_the_table(self):
        self.assertIn('id="spec-consolidate"', HTML)
        i = HTML.index('id="spec-consolidate"')
        self.assertLess(i, HTML.index('id="spec-table"'),
                        "the state reads before the rows it explains")

    def test_it_renders_nothing_when_every_unit_is_one_breakdown(self):
        self.assertIn("if (rows.length < 2) continue;", self.body)

    def test_it_speaks_the_lock_vocabulary_not_the_amber_gate(self):
        """Amber marks the one primary action in view; a list can hold
        several split units, and several ambers is no signal at all."""
        self.assertIn('"gate-strip lock-strip"', self.body)
        self.assertNotIn('className = "gate-strip"', self.body)

    def test_ids_are_courier(self):
        self.assertIn('<span class="mono">${esc(base)}</span>', self.body)

    def test_the_revision_number_comes_from_the_id(self):
        """The list rows carry no revision field — sorting on one would
        silently order the chain by whatever undefined compares as."""
        self.assertIn("const revNum = id =>", self.body)
        self.assertIn("_R(", self.body)

    def test_the_strip_wraps_rather_than_overflowing(self):
        b = re.search(r"#spec-consolidate \.lock-strip \{([^}]*)\}", CSS)
        self.assertTrue(b and "flex-wrap: wrap" in b.group(1))
        self.assertIn("UNCANONIZED — 2026-08-16 — revision consolidation", CSS)


class TheConsequenceIsStatedBeforeTheAct(unittest.TestCase):
    def setUp(self):
        self.body = fn("renderConsolidateStrips")

    def test_it_reads_the_plan_from_the_server_not_from_the_list(self):
        self.assertIn("/consolidation`)", self.body)
        self.assertIn("plan.can_consolidate", self.body)

    def test_the_confirm_names_what_survives(self):
        for probe in ("content", "snapshot each was approved against",
                      "fold into one pool", "archived inside",
                      "Nothing is deleted"):
            self.assertIn(probe, self.body, f"the confirm never says: {probe}")

    def test_it_is_not_dressed_as_a_deletion(self):
        """askConfirm's danger flag paints the act red. This one moves
        files and archives documents; nothing it touches is destroyed."""
        self.assertIn('"Consolidate into one"))', self.body,
                      "three arguments — the danger flag is not passed")

    def test_the_collapse_reopens_the_one_breakdown_that_remains(self):
        self.assertIn('uiSet("openSpec", r.base)', self.body)
        self.assertIn("renderSpecs(r.base)", self.body)


class TheRoutes(unittest.TestCase):
    def test_the_plan_is_a_read_and_the_collapse_is_a_post(self):
        self.assertIn('@app.get("/api/specs/{spec_id}/consolidation")', MAIN)
        self.assertIn('@app.post("/api/specs/{spec_id}/consolidate")', MAIN)

    def test_a_refusal_is_a_422_not_a_500(self):
        i = MAIN.index('@app.post("/api/specs/{spec_id}/consolidate")')
        seg = MAIN[i:i + 700]
        self.assertIn("except (ValueError, FileExistsError)", seg)
        self.assertIn("HTTPException(422", seg)


if __name__ == "__main__":
    unittest.main()
