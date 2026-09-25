## Context

See proposal.md. Current schema-1/2 acceptance receipts bind a separate review artifact; new tasks need a review-free path without rewriting existing approved receipts. Installed Pi policy comes from repository source and requires a separate installation to update a live agent.

## Goals / Non-Goals

**Goals:** New schema-3 contracts and evidence require only source-current checks and real observations; Pi instructions use parent self-review rather than a mandatory separate agent.

**Non-Goals:** We do not rewrite historical contracts or evidence, remove optional user-requested review tools/roles, weaken test/runtime proof, change Plane status rules or approve push/main.

## Decisions

- Add schema 3 to the existing acceptance gate instead of weakening schemas 1/2. Schema 3 rejects `reviewer` on contracts and `review` on evidence; old contracts keep their exact validation. This preserves frozen hashes and blocks accidental downgrades through edited old contracts.
- Generate a schema-3 draft with BLOCKED observations, not a fabricated PASS; the gate decides after the parent records actual results. Keep runtime provenance and regression requirements unchanged.
- Replace automatic independent-review directions at the Pi policy/skill entry points and delegated flow with parent self-review. Leave the optional reviewer role in native presets for explicit user requests.

## Risks / Trade-offs

- [No second set of eyes on security-sensitive work] → Explicitly keep test/runtime requirements and parent self-review; user may request independent review.
- [Old drafts remain blocked without review] → Preserve their schema semantics; use schema 3 only for new task contracts rather than rewriting frozen evidence.
- [Installed profiles lag source] → Report that the new policy applies to live sessions only after authorized installation and reload; local dev delivery alone is not installation.

## Migration Plan

Add schema-3 support and focused tests, update default documentation/examples and policy, validate specs, then deliver local dev commits. Rollback by reverting the new commits; existing schema-1/2 evidence is unchanged.
