# SIGNIN_BRANDING_PLAN.md — provider buttons wear provider branding

**For the coding agent.** Fixes the Google button on `/signin` + `/signup`
and adds one store-wide rule. Mock: `design_mocks/13a-signin-google.png`.
Read `STORE_DESIGN_SYSTEM.md` first. One commit per task, G1–G3.

## The rule (G3 canonizes it)

> **A sign-in option wears its provider's official button** where the
> provider publishes branding guidelines (Google does:
> developers.google.com/identity/branding-guidelines). The button is the
> provider's mark, not ours to restyle — no token colours, no Courier, no
> amber. Providers without published guidelines get our own secondary-button
> grammar with their brand icon. Our amber stays on our own actions.

## G1 — The Google button

Replace `<a class="btn btn-primary" href="/auth/google">Continue with
Google</a>` with the **dark neutral, rectangular** variant from Google's
guidelines — the right pick for this store: dark like the page, square
corners like the system, and the neutral (not blue) fill so it doesn't fight
the amber that remains on the page.

Spec (per guidelines — do not adapt to tokens):

```css
.btn-google {
  display: inline-flex; align-items: center; justify-content: center;
  gap: 10px; height: 40px; padding: 0 12px; min-width: 220px;
  background: #131314; border: 1px solid #8E918F; border-radius: 0;
  font-family: 'Roboto', var(--sans); font-size: 14px; font-weight: 500;
  color: #E3E3E3; text-decoration: none;
}
.btn-google:hover { border-color: #E3E3E3; }
.btn-google svg { width: 18px; height: 18px; flex: none; }
```

- The "G" is the **full-colour** four-colour SVG at 18px, never recoloured,
  never single-colour, on no extra white tile (the dark button variant
  carries the G directly per the current guidelines).
- Text is exactly `Continue with Google` (an approved string) in Roboto
  Medium; ship Roboto 500 locally (`app/static/fonts/`) with `var(--sans)`
  fallback — never hotlink, per the icon rule's same logic.
- Do not stretch it full-width if the guidelines' proportions break; the
  40px height and 12px padding are the spec.

## G2 — The page keeps its amber on our action

With Google wearing its own mark, `Email me a sign-in link` returns to
`btn-primary` (amber) in the `google_ready` case too — the store's fill
budget is spent on our action, and the two buttons no longer compete in the
same visual voice. The `OR` divider between them: two hairlines and a
Courier `OR`, per mock. When `google_ready` is false, nothing changes.

## G3 — Canon

Add the rule (top of this file) to `STORE_DESIGN_SYSTEM.md` — new subsection
`### 10. Provider marks` under the vocabulary section, cross-referencing the
app's icon rule (LobeHub tiles) as its sibling: *tiles identify a provider
in our chrome; sign-in buttons are the provider's chrome and follow the
provider's guidelines.* Changelog. Delete this file when shipped.
