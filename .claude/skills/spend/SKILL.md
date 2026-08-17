---
name: spend
description: You added a model call or a prompt block. Run before committing it. Every call is the customer's bill, and the failures cost more than the calls.
---

# spend — the customer's bill

Customers bring their own keys, so the app's token habits are their money.
Two directions of waste, and the second is the expensive one.

## Overspending

The pattern to emulate: the screenplay is extracted to text **once** at
import, and the raw PDF is never sent to a model. One decision, permanent
saving, on every downstream call.

Check:

- **What is in this prompt that the model cannot act on?** Measure the
  blocks. The panel prompt's largest block by a factor of four is the app
  explaining reference roles — that may be justified, but it should be
  justified on evidence.
- **Is the stable material a prefix?** Caching only works on a prefix that
  does not change. Screenplay first, instructions last.
- **Is caching actually engaged for EACH configured provider?** Not one.
  OpenAI and Gemini cache a repeated prefix automatically; Anthropic's is
  opt-in per block and needs a `cache_control` breakpoint. `INTENT.md`
  claimed caching uniformly for a month while one path cached nothing.
- **Does a retry re-send everything?** If so, say what a retry costs in
  the error message.
- **Is the same text sent twice?** The anchored scenes go once in the
  attached screenplay and again in the instructions.

## Underspending — the expensive one

Images cost far more than text, and a wasted *input* pass costs more than
the output tokens that would have avoided it.

- **What is the output ceiling, and what happens at it?**
  `MAX_OUTPUT_TOKENS = 8192` on the path producing the largest JSON meant
  the whole ~33k-token input was paid for, nothing came back, and the
  retry re-sent the screenplay.
- **Does the app read the stop reason?** If it cannot tell truncation from
  refusal, it cannot tell the user which failure they paid for.
- **Does the error say what a retry will cost?** "Expecting ',' delimiter:
  line 1 column 91" is not an error message; it is a symptom.
- **Would spending more here avoid a re-render?** A render costs orders of
  magnitude more than any prompt. Being stingy upstream of an image is
  usually a false economy.

## Before you claim a saving

Measure it, and put the number in the commit message. A prompt is not
better for being shorter, and "this looks wasteful" is not a measurement.
If quality is at stake, the honest answer is two renders compared on the
same seed and engine, judged by the user — not a reading of the code.

## Done when

- you can name what each block in the prompt is for
- caching is engaged, or the doc says which providers it is not engaged for
- the ceiling and the failure at it are both stated
- any claimed saving carries its measurement
