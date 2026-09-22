# Laya fast compaction

`pi-skill/laya-compaction/index.ts` replaces the summarization call a Pi compaction
normally spends on the span it discards. It asks the local Laya runtime two `noul`
questions per tool call in that span — keep the call, keep its result — and rebuilds
the transcript with the stale parts cut out instead of paraphrased:

- assistant and user text stays verbatim,
- a tool call stays verbatim unless Laya says both parts are spent: a stale result
  collapses to a one-line note, and a stale call plus its result disappear,
- `noul` is answered per call and per result, so the two can disagree (a result whose
  text is spent, for a call whose existence still matters),
- a kept result is capped at 4000 characters and the cap is written into the summary,
  so a compaction always frees space,
- the previous summary is carried forward verbatim because Pi drops it each cycle
  (`ponytail:` a very long session's carried chain may need folding later).

It never blocks a compaction. It declines — returning `undefined` so Pi's own
summarization runs exactly as before — when the runtime is missing, when
`/compact <instructions>` asked for a focused summary this cannot produce, on overflow
recovery (which needs a summary guaranteed to be small), when the span has no tool
calls, and when Laya judged nothing stale. A failed batch keeps everything it asked
about: a compaction that frees less beats one that loses a result.

It shares the extension's one session-scoped bridge, so compaction starts no second
model process and never loads a typed-decisions checkpoint.

## Cost and records

Two questions per call, at most 8 per request, requests in parallel — the same
question limit the tool enforces. The handler reports what it did in a Pi notification
(`<n> calls, <n> results and <n> calls dropped, <before> to <after> chars, <n> local
calls in <n> ms`) and stores the same counts under `details.laya` in the compaction
entry, next to Pi's own read/modified file lists. Every decision is in
`~/.megai/laya-calls.jsonl` with `source: "compaction"`; nothing else about the span is
recorded — never its text.

## Verification

```sh
bash tests/pi-laya.sh       # offline: fake runtime, real Pi loader, both compaction paths
bash tests/pi-laya-live.sh  # once the real checkpoints are prepared
```
