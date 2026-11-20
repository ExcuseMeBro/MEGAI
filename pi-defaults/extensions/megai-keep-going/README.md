# MEGAI keep-going

GPT models often end a run before the work is done. This extension watches Pi's
`agent_before_settle` boundary. When the final assistant message is one of these
stops, it asks for a continuation with a short "decide and finish" nudge
(`custom_message`, shown in the transcript as `megai-keep-going`):

| Kind | Example ending |
| --- | --- |
| `ask` | "Shall I…?", "qilaymi?", "aniqlashtirib bering", "Which option do you prefer?" |
| `announce` | "I will now implement X.", "Endi migratsiyani yozaman.", "Сейчас исправлю." |
| `refusal` | "too large for a single turn", "beyond the scope", "qila olmayman" |
| `unfinished` | "Remaining work:", "not yet implemented", "Qolgan ishlar", "keyingi sessiyada" |
| `plan` | a `Plan:` / `Reja:` reply from a run that called no tool |
| `not-done` | "No code changes were made.", "hech narsa o'zgartirilmadi" |

## Limits

- Up to 3 continuations per user prompt (`MEGAI_KEEP_GOING_MAX`, 1–8). A Factory task
  message (`megai-factory`) starts a fresh budget. The budget is counted from the
  transcript, so a reload does not reset it.
- The nudge gets firmer after the first time. The extension stops early if the model
  repeats the same reply, or gives two text-only answers in a row after nudges.
- It does not nudge when the final message names something only the user can clear:
  a needed secret, password or token; a main/release/tag/force push; production data;
  real money; an offline host; a memory/heavy-test gate; delegates still running; or
  `FACTORY_PAUSE`.
- It does not nudge after an aborted or errored run, when input is already queued,
  when another extension (Factory) already continued, or when the user's prompt
  itself ends with `?`.
- Offers such as "if you want, I can also…" and "Next steps:" lists only count when
  the run changed no file.

## Settings

- Applies to OpenAI/GPT models by default. `MEGAI_KEEP_GOING=all` applies it to every
  model, `MEGAI_KEEP_GOING=0` disables it.
- `MEGAI_KEEP_GOING_DEBUG=1` prints each settle decision (outcome, model, verdict; no
  message text) to stderr.

It runs no tools and changes no settings, model or thinking level. Errors fail open.
`keep-going-core.mjs` is pure and is also used by the Codex Stop hook
(`~/.codex/hooks/keep-going-core.mjs`), which keeps its old `NUDGE` and
`classifyFinal` exports. Pattern matching can miss stops or flag a finished reply.
The main fix is the autonomy text in `APPEND_SYSTEM.md` and `AGENTS.md`.
