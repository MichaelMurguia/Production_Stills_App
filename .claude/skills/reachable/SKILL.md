---
name: reachable
description: You built a capability — prove a user can reach it. Run before committing any new route, verb, or gated branch. Catches the app's characteristic defect: a feature complete end-to-end with nothing calling it.
---

# reachable — you built it; can anyone get to it?

This project's characteristic failure. Not bugs in features — **features
that do not exist because nothing calls them.**

In one day, three were found: the compiled-prompt editor, its Save, and
`unapprove_candidate`. Each was complete in `store.py` and `main.py`, each
had tests, and none could be reached from any screen. An adversarial review
then swept properly and found ten more, including `/api/projects/safety-zip`
— whose own docstring reads *"it was insurance with no way to collect it"*,
because the endpoint was written to fix that and the UI half was never
built.

The pattern is always the same: the hard half gets built, the last two
lines do not, and the tests pass because they test the hard half.

## Run this first

```
python -m unittest tests.test_every_route_is_reachable -v
```

It sweeps every `@app.<verb>` in `app/main.py` against `app.js` +
`index.html`. Green is necessary and **not sufficient** — go through the
checklist.

## The checklist

### 1. Name the caller

For each route or verb you added, say out loud where it is called from:
file and what the user clicks. If you cannot finish the sentence *"the user
gets here by ___"*, it is not done.

### 2. Name the surface it renders on

A response nothing renders is the same defect one layer up. Where does the
returned value appear? If the answer is "it does not yet", say so in the
commit rather than implying the feature landed.

### 3. Can the branch that calls it still be reached?

**The question a route sweep does not ask.** A caller can exist and be
dead.

`SLOT_OFFERED` in the arrange room renders a gate row and a `Keep` button
that PUT to `/api/specs/{base}/board-keeps/{panel}`. The routes have
callers, so the sweep is clean — but `SLOT_OFFERED` derives from a map that
is empty for every consolidated production, so the row can never appear.
The verb is dead one layer below the route.

Ask it whenever a ruling retires a mechanism rather than a deletion
removing it: **is the condition that shows this control still satisfiable?**

### 4. Is it gated, and does the gate read as state?

If the control is conditional, check the disabled case too. Product rule:
a gate is readable as state **before** it is hit — the disabled control,
the unmet condition beside it, and a link to where it gets resolved. A
control that simply vanishes is unreachable by another name; a control that
errors after the click is the gate rule broken.

### 5. Extend the sweep, or exempt it explicitly

If the route legitimately has no JS caller, add it to `SERVER_TO_SERVER` in
`tests/test_every_route_is_reachable.py` **with its consumer named**. If it
is retired but not yet deleted, add it to `RETIRED` **with the finding that
retired it** — that list is a to-do, and it only shrinks.

Never silence the test by relaxing the match.

## What this skill is not

It does not review the feature's design — `/design-verify` owns that, and a
reachable feature can still be the wrong feature. It only answers: **can a
user get to it, and does the thing they reach do what it says?**

## Done when

- the sweep is green, and any exemption you added names its consumer
- you can say who calls it and what renders it
- you have checked the branch is still satisfiable, not just present
- the disabled state states its condition
