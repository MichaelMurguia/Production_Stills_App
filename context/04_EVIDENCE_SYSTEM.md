# Evidence System

## Evidence Classes

- `SCRIPT_EXPLICIT` — directly stated or visibly required by the current screenplay.
- `SCRIPT_NECESSARY_INFERENCE` — unavoidable physical inference required to depict explicit action.
- `VISUAL_CANON_LOCKED` — explicitly approved and recorded visual canon.
- `USER_DIRECTED` — current explicit user instruction.
- `STRONG_INFERENCE` — strongly supported synthesis that does not alter plot or ownership.
- `WEAK_INFERENCE` — plausible but nonessential inference; tightly budgeted.
- `PROPOSED_NOT_CANON` — design exploration only.
- `UNSUPPORTED` — no acceptable evidence; must be removed.

## Required Evidence Record

Every intended visible object must record:

- unique object ID
- name
- panel ID
- evidence class
- source citation or reference ID
- confidence
- status: `PASS`, `HOLD`, or `REMOVE`
- rationale

A panel cannot pass if any required object is `HOLD` or `REMOVE`.
