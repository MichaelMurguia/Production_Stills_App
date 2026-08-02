# CONNECTORS_PLAN.md — auto-listing image engines in Settings

**For the coding agent.** Research completed 2026-08-03 (live-verified
endpoints, sources at bottom). Goal: the app lists current image-generation
models automatically through provider **connectors** in Settings, so the
dropdowns stay current without code changes. We do not become an
aggregator — we stay a production-design tool that plugs into them. One
task per commit, N1–N6. Builds on the existing `custom_engines` spine
(`app/generate.py`), which stays untouched as the "your own endpoint" path.

---

## Why connectors, not more built-ins

The model market turns over monthly; hand-wiring providers loses that race.
The stable layer is the **aggregator catalog API**: a handful of gateways
each expose hundreds of current models behind one key and one list
endpoint. Research verdict (§Research below): **fal.ai + OpenRouter cover
essentially every flagship image model shipping in mid-2026**, Replicate
adds the community long tail. One connector = one key = a self-updating
catalog.

## The two hard filters (what "staying focused" means in code)

1. **Reference conditioning is the product.** Canon-locked generation needs
   models that accept image input (up to `MAX_REFERENCE_IMAGES=14` today).
   A model that cannot take references cannot anchor a face or a vehicle.
   Catalog sync must read modality metadata (`text+image->image` vs
   `text->image`) and the app must state the difference — t2i-only models
   are still listable (style studies) but wear their limit.
2. **Native resolution honesty.** Renders are never upscaled. Every model
   record carries its true max output; selectors state it (`2K MAX`), and
   the existing undersize-flag flow does the rest. (This alone disqualifies
   e.g. Higgsfield Soul at 2048px from 4K board work.)

## Internal model record (N1) — align with the de-facto standard

No ratified standard exists; OpenRouter's schema is the closest lingua
franca and maps cleanly from every provider. Internal record:

```
{ id,                    // "openrouter:google/gemini-3-pro-image"
  connector,             // "openrouter" | "fal" | "replicate"
  provider_model_id,     // the connector's native id / endpoint_id
  label, developer,
  task,                  // HF-style: "text-to-image" | "image-to-image"
  input_modalities,      // ["text","image"] — image => reference-capable
  output_modalities,
  max_refs,              // int or null (unknown → state it, assume 1)
  max_px,                // longest-edge native ceiling, null = unknown
  aspect_enum,           // typed constraint when the catalog states one
  price_per_image,       // decimal string or null — never invent
  status,                // "active" | "deprecated"
  fetched_at }
```

Stored per-install in `data/connectors.json` (cache + user's enabled set);
**never** in the repo. Enrichment for missing prices may come from
models.dev (`https://models.dev/api.json`) but is optional and clearly
second-source.

## Auth — "automatic authorization" honestly stated

- **OpenRouter is the only provider with true one-click auth**: OAuth PKCE
  (`openrouter.ai/auth` → `POST /api/v1/auth/keys`) provisions a
  user-controlled key without pasting. Standalone: loopback callback on
  127.0.0.1; cloud studios: callback to the workspace URL. This is the
  flagship "Connect" button.
- **Everyone else is paste-a-key** (fal `Authorization: Key`, Replicate
  `Bearer`) with the existing test-the-key pattern and a deep link to the
  provider's key page. Do not fake "auto" where the provider offers none —
  the connector card states which kind it is.

## The phases

### N1 — registry, record, cache (no UI)
`app/connectors.py`: adapter interface (`list_models()`, `test_key()`,
`generate()`), the record above, `data/connectors.json` read/write,
capability filters. Adapters injected like the provisioner's Railway
client so tests drive fakes. **Offline rule: zero network unless a
connector is configured — the air-gapped promise holds.** Cached catalog
serves when offline; empty cache states the gate.

### N2 — Settings → Connectors UI
A Connectors section beside Engines & keys: one card per connector
(status, key/Connect, LAST SYNC Courier stamp, Refresh catalog), and a
model browser — filter by task/refs/resolution, capability badges
(`REFS ≤4`, `2K MAX`, `$0.03/IMG` when true), and per-model **Enable**.
Only enabled models join the generation dropdowns (a 600-row dropdown is
not a tool). Selectors keep their existing gating grammar; every new
pattern lands in DESIGN_SYSTEM's Uncanonized table per standing rule.

### N3 — OpenRouter connector (first, because auth)
PKCE connect + `GET /api/v1/images/models` (typed param constraints,
per-image pricing) + generation via chat completions with
`modalities:["image","text"]` (base64 out). ~40 models incl. gpt-image-2,
Gemini 3 Pro Image, FLUX.2, Seedream 4.5. Known gaps: no Ideogram, no
SD3.5.

### N4 — fal connector (largest catalog)
`GET https://api.fal.ai/v1/models?category=text-to-image|image-to-image`
(public, paginated) + `expand=openapi-3.0` to derive params per endpoint.
Generation via `queue.fal.run/{endpoint_id}` (async, poll). The adapter
maps the common param shapes (prompt / image_url(s) / image_size); models
whose schema doesn't fit a known shape are listed but marked
`UNSUPPORTED SHAPE — NOT ENABLEABLE YET` — a stated gate, not a guess. No
pricing in fal's catalog; leave null or enrich via models.dev.

### N5 — Replicate connector (long tail, curated)
`GET /v1/collections/text-to-image` as the curated dropdown source (not
the raw 10k-model firehose), `latest_version.openapi_schema` for params,
predictions API for generation. Ship only if users ask — N3+N4 cover the
flagships.

### N6 — truth pass + docs + store copy
Wire `max_px` into the undersize flag, `max_refs` into anchor limits,
aspect enums into the aspect catalog (`aspect_catalog()` already models
per-engine ratio support). Update USER_GUIDE + WEBAPP_GUIDE. Only then may
the store's engine band copy grow ("or hundreds more through fal and
OpenRouter") — the true-numbers rule gates the marketing on the shipped
feature, never the reverse.

## Explicitly out

- **Higgsfield connector** — has a young API now (platform.higgsfield.ai)
  but no model-catalog endpoint, key-pair auth, and Soul tops out at
  2048px (under our 4K bar). Its models reach us through fal anyway.
  Revisit if their catalog API materializes.
- **AWS Bedrock** — SigV4 + per-region model-access workflow; wrong
  audience weight. **Segmind / AI/ML API / Fireworks** — no usable catalog
  metadata or redundant coverage. **First-party OpenAI/Gemini** — already
  built-ins; **Stability/BFL first-party** — static ~5–12 model families,
  reachable via the custom-engine path or aggregators.
- Reselling render credits in any form. The store's engine band is the
  contract: their key, their bill, our zero markup.

## Research summary (verified 2026-08-03)

| Provider | Catalog API | Modality metadata | Auth | Verdict |
|---|---|---|---|---|
| fal.ai | `api.fal.ai/v1/models` public, category filter, per-model OpenAPI | yes (category) | key | **N4** |
| OpenRouter | `/api/v1/images/models` typed constraints + pricing | best-in-class | key **+ OAuth PKCE** | **N3** |
| Replicate | collections (`text-to-image`) + per-version schema | via collection | key | N5 |
| DeepInfra | `models/list` public, `type`+pricing | yes | key | reserve |
| Runware | `modelSearch` (arch/capabilities) | yes, no pricing | key | reserve (SD/LoRA niche) |
| Together | `/v1/models` `type==image` | yes | key | thin (FLUX-only) |
| Fireworks | no image-output flag | no | key | out |
| Segmind | none | — | key | out |
| AI/ML API | `GET /models` public, `type` | yes, no pricing | key | out (reseller) |
| Stability | none (v2beta paths) | — | key | via custom engine |
| BFL | none (static family) | — | `x-key` | via custom engine |
| OpenAI | `/v1/models`, no modality (name heuristic) | no | key | built-in already |
| Gemini | ListModels, no image capability field | no | key | built-in already |
| Bedrock | `ListFoundationModels byOutputModality=IMAGE` | yes | SigV4 | out (weight) |
| Higgsfield | none (endpoint-per-model) | — | key pair | out (2048px cap) |

Sources: fal.ai/docs/platform-apis/v1/models · openrouter.ai/docs/use-cases/oauth-pkce ·
replicate.com/docs/reference/http · api.deepinfra.com/models/list ·
runware.ai/docs/platform/model-search · docs.together.ai/reference/models-1 ·
docs.bfl.ai · ai.google.dev/api/models · docs.higgsfield.ai · models.dev

---

Delete this file when N1–N6 are shipped or superseded; log each phase in
the changelogs its surface requires.
