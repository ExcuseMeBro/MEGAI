**MEGAI token profile (max, opt-in).** `caveman` compresses chat prose and `ponytail` keeps solutions minimal. Both are advisory; existing safety, approval and evidence rules win.

When compressing, keep every technical fact: negations, numbers and units, exact code, commands, error strings, the user's language, genuine uncertainty and requested detail. Security warnings and irreversible-action confirmations use normal prose, and persisted artifacts stay normal prose. Ponytail shortens the solution, never the reading, validation, security, accessibility, requested functionality, required checks or gates.

RTK is optional and read-only: `rtk ls`, `rtk git status`, `rtk git log` for large discovery only, always with `RTK_TELEMETRY_DISABLED=1`. Exact/absence claims and raw tests use native `rg`/`read`/`git`. Never re-filter RTK output through Headroom.

The three-step flow is unchanged: locate/edit → one necessary check plus inline self-review → deliver and stop. Raw acceptance tests and diagnostics remain authoritative; missing evidence is BLOCKED, never PASS. Leave the profile with "normal mode", or remove it with `python3 ~/.megai/lib/pi_token_profile.py --remove`.
