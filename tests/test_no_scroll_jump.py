"""Redrawing the panels host must not throw the reader to the top
(user 2026-08-16: "when I click on the frames in the strip the page jumps
to the top. No jump.").

`renderBoardPanels` opened by blanking its host to "Loading…". On a first
load that is honest. On a REDRAW — staging a take, saving a camera,
withdrawing an approval, saving a prompt — it collapses the document to
nothing, so the browser clamps scrollY to 0 and the card being worked in
leaves the screen. Restoring the scroll afterwards is not enough on its
own: the collapse has to not happen, or there is a visible flash of the
page folding up and springing back.

Measured over CDP at scrollY 840: drift 0."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")


def render_fn() -> str:
    i = JS.index("async function renderBoardPanels(specId)")
    return JS[i:i + 1500]


class ARedrawIsNotALoad(unittest.TestCase):
    def test_the_host_is_only_blanked_on_a_first_load(self):
        seg = render_fn()
        self.assertIn("if (!isRedraw) host.innerHTML =", seg,
                      "blanking unconditionally is what collapsed the page")

    def test_the_redraw_test_matches_a_card_that_is_actually_rendered(self):
        """The first cut of this checked `.panel-card`, which this host has
        not rendered since the workbench became one card at a time — so the
        guard was dead and the jump survived the fix. The class asserted
        here has to be the one buildWorkbench really sets."""
        self.assertIn('const isRedraw = !!host.querySelector(".wb-card");', JS)
        self.assertIn('card.className = "panel seq wb-card";', JS,
                      "if this changes, the guard above stops working silently")

    def test_the_scroll_is_put_back(self):
        seg = render_fn()
        self.assertIn("const keepY = window.scrollY;", seg)
        self.assertIn("window.scrollTo({ top: keepY, behavior: \"instant\" })", JS)

    def test_an_explicit_route_still_wins(self):
        """A link that asked to move somewhere must not be pinned in place
        by the no-jump rule."""
        self.assertIn("if (isRedraw && !_routePanel) window.scrollTo", JS)


class ASharedPanelLinkOpensThatPanel(unittest.TestCase):
    def test_the_route_selects_the_panel_before_the_room_renders(self):
        """It used to scroll a `.panel-card` into view at the tail of the
        function — a class this host stopped rendering — so the link had
        been landing on whichever panel was last open. There is nothing to
        scroll to now; selecting IS the act."""
        self.assertIn("if (_routePanel && pids.includes(_routePanel)) roomSel.panel = _routePanel;", JS)

    def test_the_dead_lookup_is_gone(self):
        self.assertNotIn('$$(".panel-card[data-pid]", host)', JS)

    def test_the_route_is_one_shot(self):
        i = JS.index("if (_routePanel) {")
        seg = JS[i:i + 300]
        self.assertIn('_routePanel = "";', seg)
        self.assertIn("syncUrl();", seg)


if __name__ == "__main__":
    unittest.main()
