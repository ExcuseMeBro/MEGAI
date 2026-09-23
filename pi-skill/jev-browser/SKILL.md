---
name: jev-browser
description: "Drive a real Chrome tab to one natural-language goal with Jev Ultrafast (`jev-browser --url --goal`). Use only when a task genuinely needs an interactive browser: filling or submitting forms, multi-step navigation behind clicks, or reading a page pi-web-access cannot fetch. Not for search, plain page fetches, or anything a plain HTTP request already answers."
managed-by: megai
---

# Jev Ultrafast browser agent

`jev-browser` runs upstream Jev Ultrafast (browser-use/jev-ultrafast, pinned commit).
Jev picks one operation and one observed element per cycle; a small text model — the
profile's own DeepSeek key — writes text only for `TYPE_TEXT`.

```bash
jev-browser --url 'https://www.google.com/travel/flights?hl=en' \
  --goal 'Find one-way flights from Zurich to London on 2026-09-20 for one adult; stop when results are visible'
jev-browser --self-check          # offline readiness: pin, model, credential sources
```

Flags: `--json` (one object per step), `--screenshots`, `--record-dir DIR`.
Exit codes: `0` done, `2` the agent chose `BLOCKED`, `1` error.

## Before a run

- Credentials resolve from the environment, the `typesafe.ai` keychain entry, and Pi's
  `auth.json` DeepSeek key. `--self-check` reports readiness and never prints a key.
  Never put credentials in `--goal` or `--url`.
- The upstream text-helper defaults already target DeepSeek (base `api.deepseek.com/v1`,
  model `deepseek-chat`, thinking disabled); set `TEXT_MODEL`/`TEXT_MODEL_BASE_URL` only
  to override, and do not set `TEXT_MODEL_REASONING=none` with DeepSeek.
- Chrome must be reachable by Browser Harness:
  `uv run --with browser-harness browser-harness --doctor` (allow remote debugging when
  asked). Tabs are owned background tabs on the user's existing Chrome profile.
- A run makes paid calls (one Jev request per cycle plus text generation) and acts on a
  real browser session. Run it only for the goal you were given.

## After a run

- `done` is the model's claim, not proof: verify the actual outcome (fetch the resulting
  URL, check the real value) before reporting success. Report `blocked` with what the page
  showed instead of claiming success.
- State the limits honestly when they matter: no shadow DOM, frames, canvas, uploads,
  pop-up tabs, nested scrolling or arbitrary keyboard widgets; the DOM reader covers
  common HTML and ARIA controls.
- Never retry a browser mutation blindly, and never inject site-specific scripts or
  invented field values into the goal.
