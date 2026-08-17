---
name: one-rule
description: This question is now answered in two places. Run whenever a predicate is written in both Python and JS, or twice in Python. Catches the drift that shows a green marker while the render gets nothing.
---

# one-rule — one question, one implementation

The second-commonest failure here, after unreachable features. A question
gets asked in two places, the two answers drift, and the app shows one
thing while doing another.

Real ones, all found in two days:

- **"Does this phrase name that thing?"** had FOUR implementations. The
  workbench showed a green `REF` marker while the render received no
  reference, because the marker's rule and the prompt's rule disagreed.
- **"Which roles auto-attach?"** had two lists *in the same file* —
  `AUTO_ATTACH_HEADS` with the correct four, and `isAutoStyle` with two.
  The manifest read the wrong one, on the screen where money is spent.
- **"Does this take fill this slot?"** had three — the tile, the drag HUD,
  and the server. The HUD was never pessimistic, so the user read `OK`,
  let go, and watched it flip to `SHORT`.
- **"Which evidence rows justify this panel?"** had two, under a comment
  asserting they shared one list.

That last one is the tell. **A comment claiming a sharing that does not
exist is worse than no comment**, because the next reader trusts it and
changes one side.

## The checklist

### 1. Does a shared helper already exist?

Look before writing. `AUTO_ATTACH_HEADS` was already right and already in
the file. `insights.quote_is_in_screenplay` and
`store.evidence_rows_for_panel` exist now precisely so the next caller
does not write a fifth version.

Homes for shared primitives:
- `app/validation.py` — stdlib-only, imported by both sides. Naming
  primitives live here (`NAME_STOPWORDS`, `norm_name`, `word_in`).
- `/api/state` or `/api/settings` — for a list the client needs. Ship it;
  do not copy it.
- A server endpoint — when the client would otherwise re-derive something
  the server already computes. `resolved_attachments` is the pattern:
  answer with the code that actually does the work.

### 2. If the two genuinely must differ, is the DIFFERENCE the only thing that differs?

Sometimes two callers need different *policy* — the identity block refuses
on a word two cards share, the plate-offer rule matches both. That is
legitimate and deliberate.

But the **primitives** must be shared, and the divergence must be:
- documented at **both** sites, saying why, and
- pinned by a test at **both** sites.

The 2026-08-17 failure was exactly this: the policies were deliberately
different and documented, and the *primitives* had silently diverged
because a fix landed on one side only.

### 3. Is the shared half actually shared, or only claimed to be?

Read the comment above the duplication. If it says "one list, read by
both", verify that. Grep for the helper and count the callers.

### 4. When you fix one side of a cross-language pair, fix its test fixture

**The rule that would have caught the worst one.** A defect was fixed on
the client, and the server's test fixture carried a *paraphrase* of the
user's cast rather than the cast itself — so the colliding card was
missing, the collision never happened, and the suite stayed green over a
bug the user had reported.

A fixture for a cross-language fix carries the reporting user's real data.

## Done when

- one implementation, or a documented-and-tested divergence at both sites
- no comment claims a sharing that does not exist
- the fixture on the other side contains the case that was reported
