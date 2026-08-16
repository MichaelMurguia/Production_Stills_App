"""The cinematography grammars, read from `docs/CINEMATOGRAPHY_STYLES.md`.

User ruling 2026-08-16: the eight styles in that document replace the
seven light-behaviour looks the picker shipped with. They are parsed, not
copied — the document is the source of truth and the one the user
maintains, so editing it updates the app and there is never a second list
to keep in step. A style the document drops disappears from the picker;
a style it gains appears there.

What the card shows comes straight from the document's own headings:
title and subtitle from the `# n. Name — Subtitle` line, then Key
Question, Description, Operating Principle, and — behind a link, because
it runs to a page — the Image-Model Prompt.

`value` is what actually rides a render, and it is deliberately NOT the
full prompt: the document's own Usage Note says generation should rely on
the visual mechanics and operating principle rather than asking a model
to imitate a named film. So the directive is the style, its principle and
its mechanics; the reference films stay human-facing context.
"""
from __future__ import annotations

import re

from . import paths

_HEAD = re.compile(r"^#\s+(\d+)\.\s+(.+?)\s+[—-]\s+(.+?)\s*$", re.M)


def _doc_path():
    return paths.ROOT / "docs" / "CINEMATOGRAPHY_STYLES.md"


def slug(name: str) -> str:
    return "cine-" + re.sub(r"[^a-z0-9]+", "-",
                            str(name).lower()).strip("-")


def _subsections(body: str) -> dict[str, str]:
    out, cur = {}, None
    for ln in body.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", ln)
        if m:
            cur = m.group(1).strip()
            out[cur] = ""
        elif cur is not None:
            out[cur] += ln + "\n"
    return {k: v.strip() for k, v in out.items()}


def _bullets(text: str) -> list[str]:
    out = []
    for ln in text.splitlines():
        t = ln.strip()
        # `---` is the document's section rule, not a fifth reference film.
        if not t.startswith(("-", "*")) or set(t) <= {"-", "*", " "}:
            continue
        out.append(re.sub(r"^\s*[-*]\s*", "", t).strip())
    return out


def _fenced(text: str) -> str:
    m = re.search(r"```(?:text)?\n(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip()


def _avoid(prompt: str) -> list[str]:
    """The prompt's own Avoid list becomes the card's NOT fence — the
    document already states what each grammar is not."""
    m = re.search(r"^Avoid:\s*$(.*)", prompt, re.M | re.S)
    if not m:
        return []
    out = []
    for ln in m.group(1).splitlines():
        t = ln.strip()
        if not t:
            if out:
                break
            continue
        out.append(t)
    return out


def styles() -> list[dict]:
    p = _doc_path()
    if not p.exists():
        return []
    text = p.read_text(encoding="utf-8")
    heads = list(_HEAD.finditer(text))
    out = []
    for i, m in enumerate(heads):
        body = text[m.end():heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        sub = _subsections(body)
        name, subtitle = m.group(2).strip(), m.group(3).strip()
        prompt = _fenced(sub.get("Image-Model Prompt", ""))
        mechanics = _bullets(sub.get("Visual Mechanics", ""))
        principle = sub.get("Operating Principle", "").strip()
        # The directive: the style, its principle, its mechanics. Never the
        # film titles — the document is explicit that those stay context.
        value = "; ".join(x.rstrip(".") for x in
                          [f"{name} cinematography — {subtitle.lower()}",
                           principle.rstrip(".")] + mechanics[:6] if x)
        out.append({
            "n": int(m.group(1)), "key": slug(name), "name": name,
            "subtitle": subtitle,
            "question": sub.get("Key Question", "").strip(),
            "description": sub.get("Description", "").strip(),
            "principle": principle,
            "mechanics": mechanics,
            "films": _bullets(sub.get("Reference Films", "")),
            "avoid": _avoid(prompt),
            "prompt": prompt,
            "value": value[:600],
        })
    return sorted(out, key=lambda s: s["n"])
