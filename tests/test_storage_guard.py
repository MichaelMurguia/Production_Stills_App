"""Disk space is a gate, not a 502 (user 2026-08-07).

Region repair on a live studio returned:

    POST …/candidates/CAND-0066/repair failed (502) —
    {"detail":"region repair failed: [Errno 28] No space left on device"}

A cloud studio is one Railway service with one volume mounted at
SCREENBOARD_HOME. Takes are never upscaled, so a 4K PNG is 20–40 MB and
every one is kept until it is rejected AND deleted — and nothing measured
the volume, warned about it, or refused a write that could not fit. The
first sign of a full disk was a paid render dying half-written.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import generate, paths, storage  # noqa: E402

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")


class TheGuard(unittest.TestCase):
    def test_it_refuses_before_the_spend(self):
        with mock.patch.object(storage, "free_bytes", return_value=10 * 1024 * 1024):
            with self.assertRaises(storage.OutOfSpace) as cm:
                storage.require_room(what="this take")
        msg = str(cm.exception)
        self.assertIn("Not enough disk space for this take", msg)
        self.assertIn("nothing was charged", msg)
        self.assertIn("rejected takes", msg, "it must say how to reclaim")

    def test_it_allows_a_healthy_disk(self):
        with mock.patch.object(storage, "free_bytes", return_value=50 << 30):
            storage.require_room()          # must not raise

    def test_an_unmeasurable_disk_never_blocks(self):
        """A guess must not stop the app from working."""
        with mock.patch.object(storage, "free_bytes", return_value=0):
            storage.require_room()

    def test_the_headroom_covers_a_4k_take(self):
        self.assertGreaterEqual(storage.RENDER_HEADROOM, 100 * 1024 * 1024)

    def test_every_render_path_is_guarded(self):
        """Repair was the one that failed; the others write the same kind
        of file and would have failed the same way."""
        import re
        src = (ROOT / "app/generate.py").read_text(encoding="utf-8")
        for fn, what in (("def repair_region", "this repair"),
                         ("def rerender_full", "this re-render"),
                         ("def generate_panel", "this take"),
                         ("def derive_materials", "this study")):
            i = src.index(fn)
            # bound the function properly — a fixed slice silently stops
            # covering it as it grows
            m = re.search(r"\n(?=def |@app)", src[i + 1:])
            body = src[i:i + 1 + m.start()] if m else src[i:]
            self.assertIn(f'_require_room("{what}")', body, fn)

    def test_the_refusal_reaches_the_user_as_a_stated_error(self):
        """OutOfSpace is not a GenerationError, so it would have bypassed
        every stated-error handler and become a 500."""
        with mock.patch.object(storage, "free_bytes", return_value=1):
            with self.assertRaises(generate.GenerationError):
                generate._require_room("this take")


class TheReadout(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sb-stor-"))
        self._home, self._projects = paths.HOME, paths.PROJECTS_DIR
        paths.HOME = self.tmp
        paths.PROJECTS_DIR = self.tmp / "projects"

    def tearDown(self):
        paths.HOME, paths.PROJECTS_DIR = self._home, self._projects
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_it_reports_the_volume(self):
        u = storage.usage()
        self.assertGreater(u["total"], 0)
        self.assertIn("breakdown", u)

    def test_it_names_what_is_using_the_space(self):
        base = paths.PROJECTS_DIR / "show"
        (base / "data" / "boards" / "SPEC").mkdir(parents=True)
        (base / "data" / "boards" / "SPEC" / "CAND-0001.png").write_bytes(b"x" * 5000)
        (base / "data" / "references" / "originals").mkdir(parents=True)
        (base / "data" / "references" / "originals" / "r.png").write_bytes(b"x" * 1000)
        (base / "pre-import-20260807-120000.zip").write_bytes(b"x" * 3000)
        rows = {r["kind"]: r["bytes"] for r in storage.breakdown()}
        self.assertEqual(rows["Takes and boards"], 5000)
        self.assertEqual(rows["References"], 1000)
        self.assertEqual(rows["Safety copies"], 3000)

    def test_the_biggest_kind_is_first(self):
        base = paths.PROJECTS_DIR / "show"
        (base / "data" / "boards").mkdir(parents=True)
        (base / "data" / "boards" / "big.png").write_bytes(b"x" * 9000)
        (base / "data" / "references").mkdir(parents=True)
        (base / "data" / "references" / "small.png").write_bytes(b"x" * 10)
        self.assertEqual(storage.breakdown()[0]["kind"], "Takes and boards")

    def test_empty_kinds_are_not_listed(self):
        (paths.PROJECTS_DIR / "show" / "data").mkdir(parents=True)
        self.assertEqual(storage.breakdown(), [])

    def test_human_reads_as_a_size(self):
        self.assertEqual(storage.human(2 << 30), "2.0 GB")
        self.assertEqual(storage.human(5 << 20), "5.0 MB")


class TheReadoutUI(unittest.TestCase):
    def test_it_states_the_refusal_threshold_not_just_a_bar(self):
        self.assertIn("A RENDER WOULD BE REFUSED", JS)
        self.assertIn("GETTING TIGHT", JS)

    def test_a_healthy_disk_carries_no_colour(self):
        i = JS.index("const state = tight")
        self.assertIn('tight ? "bad" : s.low ? "hold" : ""', JS[i:i + 120])

    def test_it_says_how_to_reclaim(self):
        self.assertIn("Reject a take, then Delete", JS)


if __name__ == "__main__":
    unittest.main()
