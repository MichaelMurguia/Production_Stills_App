"""Every route a user needs must be reachable from the UI.

This codebase's characteristic defect. In one day three capabilities were
found built end to end with no caller — a prompt editor, its Save, and
`unapprove_candidate` — each complete in `store.py`/`main.py` and
unreachable from any screen. The adversarial review then swept properly and
found ten more (F9), including `safety-zip`, whose own docstring reads *"it
was insurance with no way to collect it"* because the endpoint was added to
fix exactly that and the UI half was never built.

The existing test covered `POST /api/specs/{id}/candidates/{id}/*` only —
one shape out of 143 routes.

Two kinds of exemption, both of which must be NAMED rather than inferred:

- `SERVER_TO_SERVER` — a real consumer that is not this app's JS.
- `RETIRED` — a route whose mechanism is being deleted. It carries the
  finding that retired it, so the entry is a to-do rather than a shrug, and
  removing the route removes the entry.

Anything else with no caller is a feature that does not exist."""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
CLIENT = JS + "\n" + HTML

ROUTE_RE = re.compile(r'@app\.(get|post|put|delete|patch)\("([^"]+)"\)')

# Consumed by something that is not this app's JS. Each names its caller.
SERVER_TO_SERVER = {
    "/login": "server-rendered login page (_LOGIN_HTML in app/main.py)",
    "/api/login": "the login form posts to it directly",
    "/connectors/openrouter/callback": "OAuth redirect target",
    "/api/preview-render": "storefront/app/main.py calls it server-to-server",
    # The server hands the client this URL in a response body
    # (main.py:1398 returns {"preview": "/api/connectors/preview-image/…"}),
    # so the caller is real but the path never appears as a literal.
    "/api/connectors/preview-image/{name}":
        "URL returned by POST /api/connectors/preview and rendered as an <img>",
}

# Routes whose mechanism is being removed. The value is the finding that
# retired it; delete the route and delete the row.
RETIRED = {
    "/api/lessons": "F2 — the project-lessons mechanism is never written to",
    "/api/lessons/remove": "F2",
    "/api/specs/{spec_id}/revisions": "F1 — revisions are retired",
    "/api/specs/{spec_id}/consolidation": "F1 — the migration runs at boot",
    "/api/specs/{spec_id}/consolidate": "F1 — the migration runs at boot",
    "/api/bible/sections": "F9 — duplicate; bible_catalog rides GET /api/specs/{id}",
    "/api/sheets/candidates": "F9 — wire to the arrange room's tray or delete",
}


def routes() -> list[tuple[str, str]]:
    return [(verb, path) for verb, path in ROUTE_RE.findall(MAIN)]


def has_caller(path: str) -> bool:
    """A caller is the path with its parameters relaxed to interpolation.
    `/api/specs/{spec_id}/panels/{panel_id}/prompt` matches
    `/api/specs/${specId}/panels/${p.id}/prompt`, and a query string or a
    trailing segment does not break the match."""
    pattern = re.escape(path)
    pattern = re.sub(r"\\\{[a-z_]+\\\}", r"\\$\\{[^}]+\\}", pattern)
    return re.search(pattern, CLIENT) is not None


class EveryRouteIsReachable(unittest.TestCase):
    def test_the_sweep_sees_the_whole_surface(self):
        """If this collapses, the test below is passing vacuously."""
        self.assertGreater(len(routes()), 100)

    def test_every_route_has_a_caller_or_a_named_exemption(self):
        orphans = []
        for verb, path in routes():
            if path in SERVER_TO_SERVER or path in RETIRED:
                continue
            if not has_caller(path):
                orphans.append(f"{verb.upper()} {path}")
        self.assertEqual(orphans, [], "routes with no caller and no named "
                                      "exemption — a feature that does not exist")

    def test_exemptions_are_not_a_dumping_ground(self):
        """Every exemption names a real route. A stale entry would hide a
        genuine orphan behind a path that no longer exists."""
        paths = {p for _, p in routes()}
        for p in {**SERVER_TO_SERVER, **RETIRED}:
            self.assertIn(p, paths, f"exemption for a route that is gone: {p}")

    def test_a_retired_route_names_the_finding_that_retired_it(self):
        for p, why in RETIRED.items():
            self.assertRegex(why, r"^F\d+", f"{p} must cite its finding")

    def test_the_retired_list_only_shrinks(self):
        """A guard on the guard: this list is a to-do, not a category. If it
        grows, something was retired without being removed."""
        self.assertLessEqual(len(RETIRED), 7,
                             "new entries belong in the code's deletion, not here")


class TheCandidateRoutesKeepTheirOwnCheck(unittest.TestCase):
    """The original narrow test, kept — it is the one that found the
    unapprove verb, and a regression there is worth naming specifically."""

    def test_every_candidate_route_has_a_caller(self):
        for verb, path in routes():
            if "/candidates/{cand_id}/" not in path:
                continue
            seg = path.rsplit("/", 1)[-1]
            self.assertRegex(CLIENT, rf"/{re.escape(seg)}[`?]",
                             f"{verb.upper()} {path} has no caller")


if __name__ == "__main__":
    unittest.main()
