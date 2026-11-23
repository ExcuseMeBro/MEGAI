# SECURITY_CONTEXT.md Schema & Authoring Rules (v1 — Scale-Invariant)

## O(1) Size & Quality Budget
- **Target length:** 60–120 lines.
- **Hard cap:** 150 lines on any repository regardless of size.
- **No inventories:** Never enumerate individual endpoints, individual database tables/models, or every domain repository file. Document **boundary mechanisms, middleware layers, and reusable security primitives**.
- **Zero generic filler:** Do not write generic reminders (*"sanitize inputs"*, *"prevent SQLi"*) without tying them to *this* repo's concrete primitive, sink, or architectural invariant.
- **Zero secret/vulnerability leaks:** Never record credentials, API keys, private internal hostnames/IPs, unpatched bugs, or exploit steps. If `visibility: public`, keep environment details architectural only.
- **Multi-zone monorepos:** Split into nested `<zone>/SECURITY_CONTEXT.md` files *only* when distinct services have genuinely different deployment/trust models (e.g., public edge API vs. internal mTLS worker). Never split just because a codebase is large.

## Required YAML Frontmatter
```yaml
---
schema_version: 1
visibility: private # private | public
last_synced_commit: <40-char git sha or "uncommitted">
---
```

## Required Sections (Exact Order)

### 1. Environment & Trust Model (Human-Verified)
Concise bullets (5–10 lines) covering:
- **Exposure & upstream controls:** Public vs. internal mesh; what upstream proxies/gateways/WAFs DO and DO NOT enforce (especially auth & header stripping).
- **Tenancy & crown jewels:** Isolation boundary (e.g., `orgId`, role model), sensitive data/tables, and Sev-0 failure modes.
- **Intentional guarantees & accepted risks:** What is intentionally public, guaranteed upstream, or legacy-exempt so agents do not raise false alarms or rewrite working trust boundaries.

### 2. Trust Boundaries & Entry Layers
A compact Markdown table (**typically 4–8 rows**, never an endpoint-by-endpoint list) mapping **architectural entry layers / mechanisms**:

| Boundary Layer | Mechanism / Location | AuthN / AuthZ Gate | Untrusted Inputs |
|---|---|---|---|
| Public HTTP surface | Routes registered before auth middleware in `src/app.mjs` | Intentional public (`is_public = 1` / health only) | Query params, headers |
| Authenticated API | All `/api/**` routes behind `authenticate(req)` | HS256 JWT + tenant `ctx.orgId` scoping | Path/query params, JSON body |

### 3. Blessed Primitives & Anti-Patterns
Concrete repo-specific `Use <primitive> (<path>) — NEVER <dangerous sink>` rules, grouped ONLY by security categories relevant to this repo (1–2 crisp bullets per category):
- AuthN / AuthZ & tenant isolation
- SQL / data queries & mass-assignment protection
- Outbound HTTP / SSRF & redirect validation
- Webhooks & cryptographic verification
- HTML rendering / XSS & object merging / prototype pollution
- Filesystem paths & subprocess / dynamic code execution
- CORS / security headers & logging / PII / secret handling

> **Accuracy & Ratcheting Rule:** Search all existing call sites of any symbol you restrict before writing a `NEVER` rule. Scope restrictions accurately to the real trust boundary (e.g., user-authenticated routes vs. HMAC-verified webhooks vs. workers). For large repos with legacy debt, **ratchet in one line** (*"Legacy callers remain in `src/legacy/**`; NEVER introduce new calls in new code or `src/v2/**`"*).

### 4. Stop-and-Flag Rules (Mandatory Escalation)
Explicit conditions where a coding agent **MUST stop, clearly warn the developer about the specific risk, and NOT silently ship the change**:
- Target **security invariant violations only** (bypassing tenant scope, weakening JWT/HMAC/replay/CORS checks, raw SQL/HTML/eval/shell injection, unvalidated redirects/egress/uploads, un-allowlisted mass assignment, leaking secrets/PII).
- Never write rules that block adding normal new features that follow Section 3's blessed primitives.
- State the required safe behavior: name the violated invariant and risk, propose the blessed alternative from Section 3, and wait for explicit confirmation.

### 5. Security Verification Commands
Exact shell commands to run after editing boundary code (test suite, security tests, linters/SAST if present). Keep concise (3–8 lines).

## Dynamic Pointer Format for `AGENTS.md`
Add a concise `## Security Context` section (2–4 lines) using coarse boundary globs (≤ 10 globs) + security intents:

```markdown
## Security Context

Read [SECURITY_CONTEXT.md](./SECURITY_CONTEXT.md) before editing `<coarse boundary globs>` — or whenever adding or modifying `<security-relevant intents>`. Skip it for pure formatting, UI copy, docs, or non-boundary utility edits outside these paths.
```
