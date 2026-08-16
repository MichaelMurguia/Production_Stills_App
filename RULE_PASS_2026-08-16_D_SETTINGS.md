# RULE_PASS_2026-08-16 — Part D: Settings

Two rows. Both ratified; one wants a device it already has elsewhere.

---

## D1 — Productions becomes Settings' first tab · RATIFIED, with a gap

The merge is right. Productions and the engine/workflow settings both answer
*what is true of this install*, and one being a page while the other was a
tab strip was an accident of when each was built. Header dropping to three
tools is fine — the band's `.nav-gap` rule already governs what sits right of
the gap, and three tools is a balance question the brand block survives.

**The one correction: mark the seam.** The row's real question is a tab strip
that mixes a LIBRARY with configuration — Productions is the only tab you
*act* on rather than *set*, and that difference should be visible before it
is clicked.

Use the device the app already has for exactly this distinction: a **gap in
the strip**, the tab-strip equivalent of `.nav-gap`. Productions, gap, then
the configuration tabs. No new component, no label, no explanation.

**First-in-order-but-not-default needs nothing on screen.** A first visit
opening `AI & engines` because nothing can run without a key is correct
behaviour and correctly invisible — it is the app resolving a blocker, and
§2.4 governs blockers that the user must act on, not ordering the user never
sees. `/productions` resolving to Settings-on-that-tab is right.

---

## D2 — An act inside a modal reports on itself · RATIFIED via A3

Ruled in full by **A3**. Everything shipped is correct; it adopts
`.busy.busy-inline` and retires the bespoke `.auth-state` markup rather than
standing up a second busy vocabulary.

The elapsed-seconds counter is the detail worth keeping deliberately: it is
the only thing that distinguishes a slow provider from a hung one, and A3
canonizes it at a three-second threshold for every third-party call in the
app — not just this modal.
