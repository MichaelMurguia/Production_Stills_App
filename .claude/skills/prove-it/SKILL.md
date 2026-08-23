---
name: prove-it
description: Audit a security or privacy claim by probing the running system rather than reading the code — sentinel values, every-route sweeps, real artifacts opened and read. Use for "is that secure?", "prove it", "can anyone see X?", "does that leak?", or before writing any claim into SECURITY.md or the privacy page.
---

# prove-it — read the artifact, not the intention

Written after the 2026-08-23 credential audit (user: *"we ask people to
paste their API key in the app... Is that secure for them? Prove it."*).
Most guarantees held. Two did not — and **`docs/SECURITY.md` asserted one
of the two as already true.** The code looked right. The probe disagreed.

That is the whole point of this skill. Reading a redaction function and
concluding "secrets are redacted" is how a wrong claim gets written down
and then cited later as evidence. Probing writes a sentinel through the
real system and goes looking for it.

---

## 1. Name the claim as a falsifiable sentence

Not "are keys safe" — that cannot fail. Write claims that a single command
can kill:

- "No HTTP route returns the key."
- "The key is in exactly one file on disk."
- "No backup zip contains it."
- "The customer download cannot contain it."
- "The app never sends it anywhere except the provider it belongs to."

If you cannot say what output would prove a claim **false**, you are about
to write reassurance, not a finding.

---

## 2. Plant a sentinel

A distinctive value you can grep for everywhere, in a throwaway home so
nothing touches the real install.

```bash
SCRATCH=<session scratchpad>; mkdir -p "$SCRATCH/sec"
OPENAI_API_KEY="" GEMINI_API_KEY="" SCREENBOARD_HOME="$SCRATCH/sec" \
  python -m uvicorn app.main:app --port 8795 > "$SCRATCH/sec.log" 2>&1 &
sleep 6
curl -s -X POST localhost:8795/api/settings -H "Content-Type: application/json" \
  -d '{"openai_api_key":"sk-SENTINEL-DO-NOT-LEAK-9f3a2b7c1e"}'
```

Blank the real env keys — a shell's `OPENAI_API_KEY` changes which code
paths run. Use a sentinel with a shape a real key has (prefix + length);
shape-based defences will not fire on `"hunter2"` and you will pass an
audit you should have failed.

---

## 3. Sweep the whole surface, not the routes you suspect

The bug is never in the route you thought of. Enumerate from the app
itself:

```python
from app.main import app
gets = [r.path for r in app.routes
        if "GET" in getattr(r, "methods", set()) and "{" not in r.path]
for p in sorted(set(gets)):
    body = urllib.request.urlopen("http://127.0.0.1:8795" + p).read()
    if SENTINEL.encode() in body:
        print("LEAK:", p)
```

42 routes took seconds and turned "the settings route masks the key" into
"no route returns it." Sweep the filesystem the same way — `grep -r` the
whole home, not just the file you expect:

```bash
grep -rl "$SENTINEL" "$SCRATCH/sec"     # expect exactly one path
grep -c "$SENTINEL" "$SCRATCH/sec.log"  # expect 0
```

---

## 4. Open every artifact the system hands out

Do not reason about what a zip contains. Build it and read its members.

```bash
curl -s -o "$SCRATCH/b.zip" "localhost:8795/api/projects/backup?slug=<slug>"
python -c "
import zipfile; z=zipfile.ZipFile(r'$SCRATCH/b.zip')
print([n for n in z.namelist() if SENTINEL.encode() in z.read(n)] or 'CLEAN')"
```

Same for the release artifact — build the **real** one, the way the
release chain does, not an approximation:

```bash
git -c core.autocrlf=false archive -o "$SCRATCH/rel.zip" HEAD -- \
  app requirements.txt run.bat README.md INSTALL.md VERSION
```

**Check you are reading the artifact you think you are.** A backup came
back clean because the app had two projects and the default backed up the
*other* one. The member list was 2 files and 147 bytes while the file on
disk was 617 — that discrepancy was the tell. Compare sizes; if a member
looks too small, it is a different file.

---

## 5. Prove the chain end to end, including the hop you assume is safe

Value-level leaks travel through code that never names the secret. When
you suspect a path, **build the adversary** — it is usually twenty lines.

For the credential audit: a local HTTP server that echoes its
`Authorization` header inside an error body, registered as a custom engine
(its `base_url` is user-supplied, so the endpoint need not be trusted).
That proved every hop:

```
exception text  →  key present verbatim
activity log    →  key written (redaction matched field NAMES, not values)
backup zip      →  key inside data/activity_log.jsonl
```

The last hop is what made it a finding rather than a curiosity: that zip
is the artifact `SECURITY.md` calls shareable. **Follow the value until it
reaches something a user hands to another person.** A leak into a file
nobody sends anywhere ranks far below one into an artifact we tell people
to share.

---

## 6. Enumerate outbound hosts

"It never phones home" is checkable, and it is the claim customers care
about most:

```bash
grep -rhoE "https://[a-zA-Z0-9.-]+" app/*.py | sort -u
```

Every host must be a provider the user chose. Anything else needs a reason
written down. (Ours has one non-provider entry: an OpenRouter attribution
header carrying no payload — verified by reading the line, not by
assuming.)

---

## 7. Separate what you can fix from what you must disclose

The audit's most useful output was not a patch. It was splitting one
muddled worry into two claims:

- **Volume compromise** — ours to fix (encrypt at rest, wrap key held
  somewhere the volume is not).
- **Operator access** — *cannot* be fixed by encryption we hold the key
  to. On a hosted product the honest answer is disclosure, or a design
  where the key never rests on our infrastructure.

Encrypting with a key stored beside the data is theater, and worse than
nothing because it licenses a sentence you have not earned. **Never write
"we cannot read your key" unless you have shipped the design that makes it
true.**

---

## 8. Write the finding so it cannot rot

- **Fix at the choke point.** Count the call sites first — `paths.SETTINGS`
  appeared in exactly 4 places, all inside load/save, which turned a
  feared refactor into ~30 lines. A grep before designing is worth an hour
  of it.
- **A regression test per finding**, carrying the reproduction in its
  docstring — the hostile endpoint, the exact chain, the date, and the
  user's words. The test file *is* the proof, frozen.
- **Correct the doc that overclaimed**, in the same commit, and say what
  changed the claim. A security doc that was once wrong and silently
  edited is worse than one that shows its correction.
- **Guard the diagnostics.** A scrubber that mangles ordinary error text
  is worse than the leak it prevents: the leak is rare, the debrief is
  every day. Test that plain messages survive untouched.

---

## Cleaning up

Kill the probe servers, delete the throwaway home and every artifact you
built, and confirm `git status` is clean before committing. A sentinel
left in a scratch file is a small mess; a real key copied somewhere during
an audit is a large one.

Never write a real credential into a test, a fixture, a commit message, or
a scratch file. Sentinels only.
