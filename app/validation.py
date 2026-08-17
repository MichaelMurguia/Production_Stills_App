from __future__ import annotations

import re

from . import paths  # noqa: F401  (installs scripts/ on sys.path first)

from validate_spec import validate  # type: ignore
from audit_spec import audit  # type: ignore


# ------------------------------------------- naming: one set of primitives
#
# "Does this phrase name that thing?" is asked by four surfaces — the REF
# marker, the first-take tick default, the SUBJECT IDENTITIES prompt block,
# and the required-object matcher — and they answered it with four rules
# that disagreed (adversarial review F10). The POLICIES differ on purpose:
# the identity block refuses on a word two cards share, because putting one
# McGuire's traits on the other writes a wrong fact into a prompt, while the
# plate-offer rule matches both, because an extra plate is one click away
# and a missing one renders a stranger's face.
#
# The PRIMITIVES must not differ, and did: `app.js` gained a stoplist and
# possessive/hyphen normalisation when the user caught both in the field,
# and the server copy never got either. This module is the home because it
# is stdlib-only and already imported by both sides; the stoplist ships to
# the client through /api/state so there is one list, not two.

NAME_STOPWORDS = frozenset({
    "the", "and", "for", "with", "from", "into", "its", "his", "her",
    "their", "that", "this", "over", "under", "onto", "off",
})

MIN_NAME_WORD = 3


def norm_name(s: str) -> str:
    """Both sides of a name comparison, normalised identically — or the
    difference between how a breakdown writes a thing and how its plate is
    filed becomes a missed match. Two real ones, both user-caught:
    "Sal's eyes" against the card SAL CRAFT (possessive), and "closing
    cryochamber" against the group SAL'S CRYO-CHAMBER (hyphen)."""
    s = str(s).lower()
    s = re.sub(r"['’]s\b", "", s)     # possessive: sal's -> sal
    s = re.sub(r"['’]", "", s)        # any other apostrophe closes up
    return s.replace("-", "")              # cryo-chamber -> cryochamber


def name_words(n: str) -> list[str]:
    """The words of a name worth matching on. Under three letters matches
    half the script; a stopword matches everything — a real reference group
    is called "P02 SHACK IN THE MEADOW", and without the stoplist every
    object containing "the" matched it."""
    return [w for w in re.split(r"[^a-z0-9]+", norm_name(n))
            if len(w) >= MIN_NAME_WORD and w not in NAME_STOPWORDS]


def word_in(needle: str, hay: str) -> bool:
    """Whole-word containment: "shop" must not match "workshop", and the
    group "SOD" must not match "sodium vapour lamp"."""
    if not needle:
        return False
    return re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])",
                     hay) is not None


def app_level_errors(spec: dict) -> list[str]:
    """Rules the schema requires but scripts/validate_spec.py doesn't enforce.
    Required objects are optional — a panel may be steered by its purpose alone
    and let the model compose within canon — but every panel needs at least a
    purpose or one required object, else there is nothing to render."""
    errors = []
    if not spec.get("panels"):
        errors.append("specification has no panels")
    for p in spec.get("panels", []):
        if not str(p.get("purpose", "")).strip() and not p.get("required_objects"):
            errors.append(
                f"panel {p.get('id')} needs a purpose or at least one required object")
    return errors


def full_validate(spec: dict) -> list[str]:
    return validate(spec) + app_level_errors(spec)


def check_spec(spec: dict) -> dict:
    """Run the deterministic governance checks from scripts/ against a spec."""
    errors = full_validate(spec)
    report = audit(spec)
    return {
        "valid": not errors,
        "errors": errors,
        "audit_decision": report["decision"],
        "audit_findings": report["findings"],
    }
