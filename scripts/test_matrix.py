"""Generate docs/TEST_MATRIX.md from the suites themselves.

The document this replaces was a review written on 2026-08-02 with
updates bolted on. By 2026-08-22 its header said "116 tests, 14 files"
over a suite of 1605 tests in 86 files, and it named 15 of them. It had
become a changelog wearing a matrix's name, and every count in it was
wrong.

So it is derived now, the same way test_step_numbers derives the wizard's
numbering and RENDERING_STYLE_PROMPTS derives its styles: the suite is the
authority, this reads it, and a test asserts the committed file is what
this produces. Add a test file and the matrix gains a row; rename one and
it follows.

What a generator cannot know — why a suite exists, which rules bind, what
is deliberately not covered — stays hand-written in PREAMBLE and NOTES
below, where it is short enough to keep true.

    python -m scripts.test_matrix [out.md]
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT_DEFAULT = ROOT / "docs" / "TEST_MATRIX.md"

SUITES = [
    ("Product app", ROOT / "tests",
     "python -m unittest discover -s tests"),
    ("Storefront", ROOT / "storefront" / "tests",
     "cd storefront && python -m unittest discover -s tests"),
]

PREAMBLE = """# Test Matrix

**Generated** — `python -m scripts.test_matrix`. Do not hand-edit: a test
asserts this file is exactly what the generator produces, so an edit here
fails the suite instead of silently drifting. The prose that a generator
cannot derive lives in the script's own PREAMBLE and NOTES.

Two suites, both green before any push (CLAUDE.md):

| suite | command |
|---|---|
| Product app | `python -m unittest discover -s tests` |
| Storefront | `cd storefront && python -m unittest discover -s tests` |

Counts are test methods parsed from source, inherited ones included. They
land within a few of a live run — close enough to see the shape of the
suite, and stable enough that this file can assert against itself.

The standing convention: **every feature or bug fix updates or extends the
tests for what it touched, in the same commit**, and a bug that reached the
user gets a regression test carrying that user's real data — the reporting
production's own hexes, the reporting screenplay's own filenames — before
the fix. Tests never touch a real install: `app.paths` is redirected to a
temp home and external services are faked.
"""

NOTES = """
## What is deliberately not covered

- **Model output quality.** No test asserts that a bible reads well or a
  render looks right; that is the user's judgement and the reason the
  product exists. What IS tested is everything measurable around it —
  that a prompt contains what it claims, that a set of colours is
  actually distinct, that a citation exists in the screenplay.
- **Live provider calls.** Every engine is faked. A test that spends
  money is a test nobody runs.
- **Pixel-perfect layout.** Captured and reviewed by eye through the
  `/design-verify` loop; only token contracts, contrast ratios and
  structural facts are asserted mechanically.

## Known flake

One storefront provisioner test can reach the real network through the
`_domain_serves` probe when a row's `url` and `railway_url` diverge — seen
once. Stub it if it recurs.
"""


def first_sentence(doc: str) -> str:
    """One line describing a suite, from its module docstring."""
    if not doc:
        return "—"
    text = " ".join(doc.strip().splitlines()[:3]).strip()
    text = re.sub(r"\s+", " ", text)
    m = re.search(r"^(.+?[.!?])(\s|$)", text)
    out = (m.group(1) if m else text).strip()
    return out[:150].replace("|", "/")


def counts(folder: pathlib.Path) -> dict[str, int]:
    """Test methods per file, parsed — never imported.

    Two earlier attempts were worse. Counting `def test_` undercounts,
    because a base class's tests run once per subclass. Asking unittest to
    discover each file is exact but CONTEXT-SENSITIVE: inside a running
    suite some files fall back and the total moves by 8, which makes a
    generated document that must match itself impossible to keep green.

    So the AST is read and in-file inheritance resolved. It is stable
    everywhere, imports nothing, and lands within a few of a live run —
    the preamble says so rather than claiming a parity it does not have.
    """
    import ast
    out: dict[str, int] = {}
    for f in sorted(folder.glob("test_*.py")):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        own: dict[str, set] = {}
        bases: dict[str, list] = {}
        for n in ast.walk(tree):
            if isinstance(n, ast.ClassDef):
                own[n.name] = {m.name for m in n.body
                               if isinstance(m, (ast.FunctionDef,
                                                 ast.AsyncFunctionDef))
                               and m.name.startswith("test_")}
                bases[n.name] = [b.id for b in n.bases
                                 if isinstance(b, ast.Name)]

        def tests_of(c: str, seen: set | None = None) -> set:
            seen = seen or set()
            if c in seen or c not in own:
                return set()
            seen.add(c)
            found = set(own[c])
            for b in bases.get(c, []):
                found |= tests_of(b, seen)
            return found

        out[f.name] = sum(len(tests_of(c)) for c in own)
    return out


def scan(folder: pathlib.Path) -> list[dict]:
    n = counts(folder)
    rows = []
    for f in sorted(folder.glob("test_*.py")):
        src = f.read_text(encoding="utf-8")
        m = re.match(r'\s*"""(.*?)"""', src, re.S)
        rows.append({
            "file": f.name,
            "tests": n.get(f.name, 0),
            "classes": len(re.findall(r"^class \w+", src, re.M)),
            "purpose": first_sentence(m.group(1) if m else ""),
        })
    return rows


def build() -> str:
    out = [PREAMBLE]
    grand = 0
    for name, folder, _cmd in SUITES:
        rows = scan(folder)
        total = sum(r["tests"] for r in rows)
        grand += total
        out.append(f"\n## {name} — {total} tests in {len(rows)} files\n")
        out.append("| File | Tests | What it holds |")
        out.append("|---|---:|---|")
        for r in rows:
            out.append(f"| `{r['file']}` | {r['tests']} | {r['purpose']} |")
        out.append("")
    out.insert(1, f"\n**{grand} tests** across "
                  f"{sum(len(scan(f)) for _n, f, _c in SUITES)} files.\n")
    out.append(NOTES)
    return "\n".join(out).rstrip() + "\n"


if __name__ == "__main__":
    dest = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else OUT_DEFAULT
    text = build()
    dest.write_text(text, encoding="utf-8")
    print(f"wrote {dest} — {len(text.splitlines())} lines")
