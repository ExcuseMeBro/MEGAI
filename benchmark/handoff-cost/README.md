# Handoff cost

What a context handoff between agents actually costs, measured from local Pi session
logs. Companion to the handoff rules in `pi-skill/delegation.md`.

```bash
python3 -B benchmark/handoff-cost/measure.py --days 14
python3 -B benchmark/handoff-cost/measure.py --days 14 --json
```

Three readings:

1. **tier split** — the expensive tier's share of reported spend. If that share is
   ~95%, routing more work to a cheaper worker moves at most the remaining ~5%, and
   the real lever is how many expensive-tier sessions start at all.
2. **handoff pairs** — an upstream session wrote a `/tmp` handoff doc and a later
   session read it, plus what fraction of the downstream session's own file reads the
   upstream session had already read. That duplicate share is the re-discovery the
   rules exist to avoid.
3. **handoff artefacts** — how many handoff docs were written and how many were ever
   read back. A doc nobody reads is paid cost with no context transfer.

Limits, stated rather than implied:

- reported cost is the session log's own counter, not a billed amount;
- only explicit `/tmp` handoff docs are paired, so the pair count is a lower bound
  and in-message handoffs count as zero;
- the fed/self comparison is per tier but not per task size, so a small group is a
  signal, not evidence;
- there is no cost-per-delivered-change here. That needs a per-task delivery receipt
  as the denominator, not session logs alone.

`python3 -B tests/handoff-cost.py` checks the measurement logic on synthetic logs.
