# Screenboard Studio

A standalone local app that builds **canon-locked art direction boards** for
a screenplay: native-4K production walls assembled from individually
generated panels, each panel justified by screenplay evidence and anchored to
approved reference images. Once you approve something, the system makes
drift structurally difficult — approved sheets are hash-locked, references
have fixed jurisdictions, every render re-anchors to approved canon, and
nothing is ever upscaled.

The engine is project-agnostic; **The Beltminers** is the proving project.
Everything runs and stays on your machine — the only network traffic is the
generation calls to the provider whose API key you saved.

## Run it

```bash
run.bat            # or: python -m app
```

Your browser opens at `http://127.0.0.1:8765`. Add a Gemini and/or OpenAI
key under Settings → Engines & keys.

## Documentation

| Document | What it covers |
|---|---|
| [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) | **The manual** — every screen, concept, recipe, and FAQ, current to the five-stage UI |
| [`APP_GUIDE.md`](APP_GUIDE.md) | Operator's reference — setup, milestones, engines, canon rules |
| [`INSTALL.md`](INSTALL.md) | Installation details |
| [`app/static/DESIGN_SYSTEM.md`](app/static/DESIGN_SYSTEM.md) | The UI contract (for anyone changing the interface) |
| [`docs/FULL_INSTRUCTIONS.md`](docs/FULL_INSTRUCTIONS.md), [`docs/SOURCE_CODE_GUIDE.md`](docs/SOURCE_CODE_GUIDE.md) | The original scripts-pipeline documentation |
| `CLAUDE.md`, `IMPLEMENTATION_PLAN.md`, `DESIGN_HANDOFF.md` | Agent-facing build documents |

## The governance core (also usable headless)

The app's canon rule engine lives in `scripts/` and works from the command
line — the same code the app calls:

```bash
python scripts/validate_spec.py examples/minimal_valid_spec.json
python scripts/compile_prompt.py examples/minimal_valid_spec.json --output render/RENDER_PROMPT.txt
python -m unittest discover -s tests -v
```

The durable creative artifact is the **Production Generation Specification**
(breakdown sheet): prompts are compiled from approved specifications, and
candidate images are judged against them before anything becomes canon.
