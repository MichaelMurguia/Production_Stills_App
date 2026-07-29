# Installation

## Requirements

- Python 3.10 or newer
- No third-party Python packages are required

## ChatGPT Project

1. Upload this complete folder or ZIP.
2. Upload the current screenplay and approved visual references separately.
3. Use `SKILL.md` as the primary project instruction.
4. Begin with:

```text
Initialize production. Audit all available canon sources, then show project state and missing dependencies.
```

## Local tools

From the package root:

```bash
python scripts/validate_spec.py examples/minimal_valid_spec.json
python scripts/compile_prompt.py examples/minimal_valid_spec.json
python scripts/audit_spec.py examples/minimal_valid_spec.json
python scripts/state_manager.py show
python -m unittest discover -s tests -v
```
