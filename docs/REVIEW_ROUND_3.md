# Review round 3 — implementation report

```
implements: REVIEW_v1.md + REVIEW_v2.md, as settled in
            docs/REVIEW_ROUND_1.md and docs/REVIEW_ROUND_2.md
suites:     1321 app · 204 storefront, green
```

## Done

| Finding | What shipped |
|---|---|
| **F21, F6, F7** | `insights.quote_is_in_screenplay` — one predicate, four callers. An unverifiable `SCRIPT_EXPLICIT` demotes to `WEAK_INFERENCE`/`HOLD` in the narrative draft (user's ruling) and to `USER_DIRECTED` on a hand-written add; a scan on an anchor miss can no longer source anything to the screenplay; `citation_check` reads a real `quote` field and reports a `SCRIPT_EXPLICIT` row with no citation. Verdict on step 06: `N OF M CITATIONS NOT FOUND`. |
| **F5, F8, F22** | `generate.resolved_attachments` answers with the render's own resolver; the client's arithmetic, its two-role `isAutoStyle` and its hardcoded cap are gone. One `shortFor()` in the arrange room, and the HUD gained `PLATE SHOWS availW × availH`. |
| **F10, F13** | Naming primitives in `app/validation.py`, stoplist shipped through `/api/settings`. Distinctiveness is now per KIND — a man and his prop are not two candidates for one slot. `store.evidence_rows_for_panel` is the one predicate the snapshot and the gate share. |
| **F9, F16, F24** | Every one of 143 routes swept, with named `SERVER_TO_SERVER` / `RETIRED` exemptions. `/api/screenplay/text` and `/api/projects/safety-zip` collected. Skills `reachable`, `one-rule`, `spend`. |
| **F17, F20, F11** | `cache_control` on the screenplay block; ceiling 8192 → 32000; `stop_reason` read; both truncation shapes named with the retry's cost. `INTENT.md` states caching per provider. |
| **F2, F12** | Lessons deleted; `prohibited_inventions` kept and explained; prompt block renamed `PROJECT RULES`; six strings corrected, including three on `Delete forever`. |
| **F23** | Migration skips collected, printed at boot, raised as a `CARE` row. |
| **F3, F4, F14, F15** | Hex contract with a `SANCTIONED` dict; three roll materials tokenised; `docs/README.md` map; `docs/history/`; root `SKILL.md` retired; `BUGFIX_PLAN` ledgered; TODOs merged. |

## Not done, deliberately

**F1 — delete the revisions machinery.** The precondition is proven and
now pinned: `tests/test_revisions_are_inert.py` shows that on consolidated
data every floor is 1, `offered` is empty, the keeps registry is inert, and
`qualifying_approved_by_panel` reduces exactly to "newest approved take per
panel". F23 shipped, and no skipped chain exists on this machine.

What remains is the refactor itself: eleven `assemble.py` call sites on the
path that produces the user's final output, plus seven routes and the UI
half. I stopped rather than attempt it at the end of a long run, because a
subtle error there silently changes which takes appear on a board and would
not be visible in any test that exists. It is the next thing, and it is now
safe to start.

**F18, F19 — both need renders, not code.** F19 is taste by the reviewer's
own filing. F18's remedy replaces quoted scene text with headings, and
`scene_anchor` does not expose headings, so taking it on reading alone
would be a quality change made blind — which is what I told the reviewer in
round 2. Both need two renders on the same seed and engine, judged by the
user.
