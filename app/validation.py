from __future__ import annotations

from . import paths  # noqa: F401  (installs scripts/ on sys.path first)

from validate_spec import validate  # type: ignore
from audit_spec import audit  # type: ignore


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
