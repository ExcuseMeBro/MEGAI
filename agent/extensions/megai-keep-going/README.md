# MEGAI keep-going

GPT models often end a run by asking for permission ("Shall I…?", "qilaymi?",
"aniqlashtirib ber") or by reporting that nothing was changed, instead of finishing
routine work. This extension watches Pi's `agent_before_settle` boundary and, when the
final assistant message looks like such a stop, requests **one** continuation per user
prompt with a short "decide and finish" nudge (`custom_message`, visible in the
transcript as `megai-keep-going`).

- Applies to OpenAI/GPT models by default. `MEGAI_KEEP_GOING=all` applies it to every
  model, `MEGAI_KEEP_GOING=0` disables it. `MEGAI_KEEP_GOING_DEBUG=1` prints each
  settle decision input (roles, model, outcome; no message text) to stderr.
- Never nudges twice for the same user prompt, after an aborted/errored run, when
  input is already queued, or when the user's prompt itself ends with `?`.
- Offers such as "if you want, I can also…" only count when the run changed no file
  (edit/write/codemode tool calls); direct permission questions always count.
- The nudge keeps the irreversible boundaries: production data, real money, main/
  release/tag/force push and spending still require the user.
- It runs no tools and changes no settings, model or thinking level. Errors fail open.

`keep-going-core.mjs` is pure and shared verbatim with the Codex Stop hook
(`~/.codex/hooks/keep-going-core.mjs`). It is a heuristic, not a guarantee; the
primary fix is the autonomy text in `APPEND_SYSTEM.md` and `AGENTS.md`.
