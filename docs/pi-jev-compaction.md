# Jev fast compaction

`pi-skill/jev-compaction/index.ts` is installed as
`extensions/megai-jev-compaction/index.ts` by `lib/pi_model_policy.py`. It replaces
Pi's LLM summarization for the span a compaction discards with two cheap TypeSafe
Jev `noul` questions per tool call in that span — keep the call, keep its result.

The outcome is a transcript with the stale parts cut out, not a paraphrase:

- user and assistant text, every tool call, and every result Jev keeps stay verbatim;
- a result judged stale collapses to one line naming the tool and its size;
- a stale call disappears together with its result;
- thinking blocks are dropped, and a kept result is capped at 4000 characters with a
  note, so a compaction always gives space back;
- the previous summary is carried into the new one, because Pi drops it each cycle.

Cost is a fraction of a cent per compaction and about a second for a handful of
parallel requests, against one provider summarization call. 8 questions per request,
two per call, so a span with many calls becomes several parallel requests.

## When it defers to Pi

The handler returns nothing — and Pi's own summarizer runs exactly as before — when
there is no TypeSafe key, when the compaction carries `/compact <instructions>` focus
text, on overflow recovery (`reason: "overflow"`, which needs a summary guaranteed to
be small), when the span holds no tool calls, when Jev drops nothing, and when the
extension cannot compute a summary at all. A Jev batch that fails or answers
unreadably keeps everything it asked about: a compaction that frees less context beats
one that silently loses a result. A successful compaction records counts, request
count and character totals under `details.jev` in the compaction entry.

## Verify

```bash
PI_PACKAGE_ROOT=<installed pi-coding-agent> node tests/pi-jev-compaction.mjs
```

The test installs through the real installer, loads through the real Pi resource
loader (so the relative import of the `jev` extension is exercised), drives the real
`session_before_compact` hook against a local fake TypeSafe endpoint, and asserts the
keep/drop outcomes, the request shape, batching, and every deferral path offline.
`tests/pi-jev.mjs` covers the shared `jevPost`/key path the two extensions share, and
`tests/pi-jev-retry.mjs` covers the 429/529 retry that path now applies to compaction
and the tool alike.

Thresholds and budgets are constants at the top of the extension; change them in
`pi-skill/jev-compaction/index.ts` and re-run the installer.
