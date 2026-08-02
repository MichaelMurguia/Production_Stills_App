"""The four-anchor ruling (2026-08-03): three movie parameters + one board
parameter auto-attach, capped per role; board layout is assembly grammar."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from app import store


def ref(rid, role, added, status="APPROVED"):
    return {"id": rid, "role": role, "status": status, "added_at": added}


class StyleAnchorTests(unittest.TestCase):
    def test_four_anchor_shelf(self):
        self.assertEqual(store.AUTO_STYLE_ROLES,
                         {"WORLD_TEXTURE", "COLOR_PALETTE",
                          "CINEMATOGRAPHY_STYLE", "BOARD_RENDERING_STYLE"})
        self.assertEqual(store.MOVIE_STYLE_ROLES,
                         ("WORLD_TEXTURE", "COLOR_PALETTE", "CINEMATOGRAPHY_STYLE"))
        self.assertNotIn("BOARD_LAYOUT_STYLE", store.AUTO_STYLE_ROLES)

    def test_attach_cap_newest_first_and_layout_excluded(self):
        refs = [
            ref("REF-1", "CINEMATOGRAPHY_STYLE", "2026-08-01T10:00:00"),
            ref("REF-2", "CINEMATOGRAPHY_STYLE", "2026-08-02T10:00:00"),
            ref("REF-3", "CINEMATOGRAPHY_STYLE", "2026-08-03T10:00:00"),
            ref("REF-4", "COLOR_PALETTE", "2026-08-01T10:00:00"),
            ref("REF-5", "BOARD_LAYOUT_STYLE", "2026-08-01T10:00:00"),
            ref("REF-6", "WORLD_TEXTURE", "2026-08-01T10:00:00", status="PROVISIONAL"),
        ]
        with patch.object(store, "_load_refs", return_value=refs):
            out = store.auto_style_references()
        ids = {r["id"] for r in out}
        # Cap: only the newest two cinematography anchors ride.
        self.assertIn("REF-3", ids)
        self.assertIn("REF-2", ids)
        self.assertNotIn("REF-1", ids)
        # Palette rides; layout never; unapproved never.
        self.assertIn("REF-4", ids)
        self.assertNotIn("REF-5", ids)
        self.assertNotIn("REF-6", ids)


if __name__ == "__main__":
    unittest.main()
