# Beltminers Production Art Director v2

A source-complete, renderer-agnostic production-art workflow for **The Beltminers**.

The system treats the **Production Generation Specification** as the durable creative artifact. Prompts are compiled from approved specifications and candidate images are audited against those specifications before approval.

## Included

- ChatGPT skill instructions
- production context and governing rules
- agent definitions
- reusable templates
- JSON Schemas
- Python command-line utilities
- project-state files
- examples
- unit tests
- full operating documentation

## Quick start

```bash
python scripts/validate_spec.py examples/minimal_valid_spec.json
python scripts/compile_prompt.py examples/minimal_valid_spec.json --output render/RENDER_PROMPT.txt
python scripts/state_manager.py show
python -m unittest discover -s tests -v
```

See `docs/FULL_INSTRUCTIONS.md` and `docs/SOURCE_CODE_GUIDE.md`.
