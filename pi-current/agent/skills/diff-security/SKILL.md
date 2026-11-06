---
name: diff-security
description: Fast security review of your own code diff before delivery. Use for every agent-authored code change; escalates to security-audit only for high-risk diffs.
---

# Diff security review

Review the complete changed-code diff once, after tests pass and before delivery.
Read-only; no artifacts. Report "security: <n> findings fixed / none / unverified: X".

## 1. Classify the diff (10 seconds)

High-risk if it adds or changes any of: authentication, sessions, tokens, password or
key handling, authorization/role/permission/tenant checks, money movement or balance
math, crypto, deserialization or parsing of untrusted input, shell/SQL/template/eval
construction, file paths or uploads, outbound requests to user-supplied URLs (SSRF),
CORS/CSP/cookie flags, dependency additions, CI/release scripts.

- High-risk: also read `security-audit/SKILL.md` (guidance mode: "Core principles")
  and the one companion file for the touched area (e.g. WEB-PROTOCOL-AND-AUTH.md,
  DATA-ISOLATION-AND-LIFECYCLE.md, SUPPLY-CHAIN-AND-RELEASE.md). Never the full audit.
- Otherwise: this checklist is the whole review.

## 2. Checklist (only lines the diff touches)

- Input: every new external input (request field, header, query, file, env, message)
  is validated for type/size/range at the boundary; no trust in client-sent ids,
  prices, roles, tenant or owner.
- Authz: each new/changed endpoint or action checks the caller may act on THIS
  resource (owner/tenant/role) server-side, including list/export/bulk variants.
- Injection: queries parameterized; no string-built shell, SQL, HTML, regex from input;
  output escaped for its context.
- Secrets: none in code, logs, errors, tests or commits; errors do not leak internals.
- Money/state: amounts use exact types; balance changes are atomic (transaction/lock)
  and idempotent on retry; audit trail written where the domain expects one.
- Files/URLs: paths normalized and confined; uploads type/size-limited; fetch targets
  allowlisted.
- Dependencies: new packages are necessary, pinned, and from the expected source.

## 3. Act

A finding needs a concrete path: lower-trust actor → input → missing control →
affected resource/result. Fix it at the last trusted decision point, add a regression
test, rerun affected tests. Missing best practice without a reachable path is a note,
not a blocker. Unresolvable facts (deployment, proxy, provider settings) are reported
as unverified, not guessed.
