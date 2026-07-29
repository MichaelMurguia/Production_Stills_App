# Source Code Guide

## Python tools

- `scripts/validate_spec.py` — deterministic structural and canon-budget checks.
- `scripts/audit_spec.py` — adversarial specification audit and contradiction checks.
- `scripts/compile_prompt.py` — deterministic prompt compiler with stable spec hash.
- `scripts/create_spec.py` — creates a starter JSON specification.
- `scripts/state_manager.py` — reads and updates persistent project state.
- `scripts/export_package.py` — creates a source ZIP from the current tree.
- `scripts/common.py` — shared JSON, hashing, and formatting helpers.

All scripts use only the Python standard library.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Important limit

The source utilities validate structure, evidence budgets, state, and prompt compilation. They do not replace screenplay research or visual inspection. Those remain agent responsibilities defined in `agents/` and `SKILL.md`.
