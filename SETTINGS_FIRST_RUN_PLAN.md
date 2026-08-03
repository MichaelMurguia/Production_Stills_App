# SETTINGS_FIRST_RUN_PLAN.md — the page has two lives

**For the coding agent.** Replaces the shipped AI & engines tab's empty state.
Mocks: `design_mocks/18a-settings-first-run.png` (first run) and
`18b-settings-configured.png` (steady state). Read
`app/static/DESIGN_SYSTEM.md` first. One task per commit, F1–F7.

## The defect being fixed

A fresh install renders the steady-state layout with no data behind it: two
dropdowns whose only option is `NO OPENAI KEY — ADD ONE IN 02 BELOW`. Every
new user meets a control that is an error message pointing further down the
page.

**Canonical rule** (Layout patterns):

> Before a credential exists the page is a setup form; after one exists it is
> a control panel. A dropdown is never an error message, and a control that
> cannot act does not render as a control.

## F1 — The switch

Key the whole tab on the existing credential check. Zero credentials → the
18a layout. Any credential → the 18b/turn-17 layout with real selectors.
Partial setup (e.g. Gemini key, no OpenAI): 18b layout, with the withheld-verb
tag `NEEDS THE OPENAI KEY` in place of the narrative selector — the dashed
tag, never a disabled dropdown.

## F2 — First-run layout (mock 18a), top to bottom

1. **Recommended quick start** — left column:
   - Courier eyebrow `RECOMMENDED QUICK START` in `--accent`.
   - Heading: **Connect to many models.**
   - One amber button: `Connect OpenRouter →` with Courier
     `ONE CLICK · NOTHING TO PASTE` beside it. This is the page's only amber.
   - The three-step Courier chain in bordered chips:
     `SIGN IN AT OPENROUTER.AI → APPROVE → A KEY YOU CONTROL COMES BACK`.
   - The provider marquee (F4).
   - Footer: `400+ MODELS · 70+ PROVIDERS · ONE CREDIT BALANCE PAYS FOR ALL · REVOKE ANY TIME`.
2. **Notice column** — right, hairline-divided, editorial (no box, no chrome):
   a 34×2px `--accent` rule, then "New to using AI models?" and the
   recommendation paragraph; below it "AI model pro?" and the any-model-any-
   role paragraph. Copy verbatim from the mock.
3. **OR ADD YOUR ACCOUNTS** — one bordered list: OpenAI, Google Gemini,
   Anthropic Claude, each with its brand icon and one `Authenticate` button
   (ghost, bordered) that opens the credential modal. No status chips, no
   subtitles, no "Add key" links. Last row: **Your own endpoints** ·
   `ADD ANY API KEY` · `Add model`.
4. **SET DEFAULT MODELS** — the two role rows as inert dashed withheld-verb
   tags (`WILL RUN ON ChatGPT gpt-5.6` / `WILL RUN ON THE FIRST ENGINE YOU
   ADD`). No dropdown chrome. No zero-count stat tiles anywhere on first run.

## F3 — The OpenRouter connect (PKCE)

Their documented one-click flow, no app registration:

1. Generate `code_verifier`; send the user to
   `https://openrouter.ai/auth?callback_url=<app>&code_challenge=<S256 hash>&code_challenge_method=S256`.
2. User signs in and approves; redirect returns `?code=…`.
3. Exchange at `POST https://openrouter.ai/api/v1/auth/keys`
   (`{code, code_verifier, code_challenge_method}`) → a **user-controlled API
   key**. Store it exactly like a pasted key in `data/settings.json`.

On success: set narrative default to gpt-5.6 and image default to the GPT
Image 2 route **via OpenRouter**, per the notice's promise. The standalone
build runs the same flow with a localhost callback.

## F4 — The provider marquee

A masked, auto-scrolling strip of ~16 provider tiles (icon + name) under the
Connect button — the "there are many" widget. CSS keyframe translate of a
duplicated sequence, ~36s loop, `mask-image` fade at both edges.

**Icons: LobeHub static set, dark variants** — favicons fail here (OpenAI's
and xAI's marks vanish on dark; Google's favicon service returns the wrong
logo for Gemini). Fetch once at build time from
`https://unpkg.com/@lobehub/icons-static-png@latest/dark/<slug>.png` into
`app/static/provider-icons/` and serve locally — never hotlink at runtime.
Slugs used in the mock: `openai, claude-color, gemini-color, meta-color,
mistral-color, deepseek-color, qwen-color, xai, nvidia-color, aws-color,
cohere-color, perplexity-color, minimax-color, moonshot, nousresearch,
liquid` (`liquid-color` does not exist — use `liquid`).

The same three icons (openai, gemini-color, claude-color) go on the account
rows' 36px tiles.

## F5 — The Authenticate modal

One modal per provider: icon, name, one key field, `Test & save`, and a deep
link to that provider's key page. This is where pasted keys live now — the
hero form is gone. Reuse the existing key-test endpoints.

## F6 — Claude as a narrative provider — NEEDS BACKEND

The Anthropic row implies the narrative role accepts a second provider
(`claude-opus-5`). Today the role is hard-wired to the OpenAI key. Wire the
narrative selector to accept any connected chat-capable credential
(direct Anthropic, or any chat model via OpenRouter). If that lands later,
ship the row anyway and let its Authenticate store the key for when the
selector learns to use it — but say so in the modal:
`STORED — USED ONCE NARRATIVE MODEL SELECTION SHIPS`.

## F7 — Copy and canon

- Section headers: `OR ADD YOUR ACCOUNTS`, `SET DEFAULT MODELS` (renamed from
  `01 — WHAT WILL RUN`).
- All first-run annotations are gone by design — no data-location footnotes,
  no network-promise lines, no rationale cards. Form follows function; the
  page carries required information only.
- Add to `DESIGN_SYSTEM.md`: the two-lives rule (F1), the marquee pattern and
  icon source (F4), and the one-amber-per-page placement on the quick start.
  Changelog it. Delete this file when done.
