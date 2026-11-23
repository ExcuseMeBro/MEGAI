---
name: security-context
description: >-
  Generate or continuously update a concise, scale-invariant SECURITY_CONTEXT.md
  and wire a dynamic trigger pointer into AGENTS.md so coding agents write more
  secure code and proactively flag security boundary violations. Works on any
  repository regardless of size while keeping SECURITY_CONTEXT.md O(1) in length.
---

# Security Context Skill

Create and maintain `SECURITY_CONTEXT.md` (at the repository root, or per independent trust zone in a multi-service monorepo) plus a concise, repo-specific trigger block in `AGENTS.md` (and `CLAUDE.md` if used separately).

Read [references/schema.md](./references/schema.md) before writing or updating `SECURITY_CONTEXT.md`.

## Core Principles

1. **O(1) size on any repository.**
   `SECURITY_CONTEXT.md` MUST NOT grow with lines of code, file count, or endpoint count. Document **architectural mechanisms, boundary layers, and reusable security primitives**—never an inventory of individual routes, models, or files. Target **60–120 lines** (hard cap: **150 lines**).
2. **Repo-specific signal only — zero generic OWASP filler.**
   Coding agents already know generic security advice. Every bullet must name *this* repository's concrete trust boundary mechanisms, blessed primitives (exact file path & symbol), dangerous sinks/legacy traps, and environment-specific invariants.
3. **Discover first (top-down & search-driven), interview second.**
   Never ask the user what the code already tells you, and never brute-force read an entire repository. Map the perimeter, trace from entrypoints inward, use search (`rg`/`grep`/glob) to locate security primitives and sinks, and only ask the human for un-inferrable environment, trust, and risk context.
4. **Defensive invariants, never an attacker's roadmap.**
   Never write unpatched vulnerabilities, exploit steps, internal IPs/hostnames, or credentials into `SECURITY_CONTEXT.md`. Document what *must* hold true, not how to exploit the app.
5. **Preserve human intent on updates.**
   Continuous syncs must preserve human-verified environment context, accepted risks, and custom Stop-and-Flag rules unless a real trust-boundary change requires asking the user.

---

## Mode Selection

- **`init` mode:** `SECURITY_CONTEXT.md` does not exist yet (or the user asked to regenerate from scratch).
- **`sync` mode:** `SECURITY_CONTEXT.md` already exists and has `last_synced_commit` in its YAML frontmatter.
- **`check` mode:** Verify whether `SECURITY_CONTEXT.md` is stale or malformed using `node <skill-dir>/scripts/detect-drift.mjs` (or `git diff <last_synced_commit>..HEAD`) without editing files.

---

## Workflow: `init` Mode (Scale-Invariant Agentic Discovery)

### Step 1: Top-Down, Search-Driven Discovery (Never Read-All)
Follow this bounded exploration order so discovery stays fast and accurate on any codebase:

1. **Perimeter & Topology (top-level only):**
   - Inspect top-level directories, project manifests (`package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, etc.), deployment/IaC configs (`Dockerfile`, k8s, terraform, ingress/proxy configs), and existing `AGENTS.md`.
   - Decide whether this repo is **one trust zone** (one root `SECURITY_CONTEXT.md`) or a **multi-zone monorepo** with genuinely distinct deployments/trust models (e.g., public web gateway + internal mTLS worker). *Split only by distinct trust model—never merely because a codebase is large.*
2. **Trace Entrypoints Inward (request/execution lifecycle):**
   - Locate the central server bootstrap, root router, middleware chain, RPC/GraphQL schema entry, webhook dispatcher, or CLI entrypoint.
   - Read those central wiring files to see *where* AuthN, AuthZ, CORS/headers, parsing, and error handling are enforced as a layer.
3. **Search by Security Capability (sample, don't crawl):**
   - Use targeted searches (`rg`/`grep`/glob) to locate the repo's **central security primitives and high-risk sinks**:
     - AuthN / AuthZ / JWT / session / RBAC / tenant-scoping wrappers
     - Database/ORM access layer & raw query / dynamic SQL builders
     - Outbound HTTP clients / SSRF guards & redirect validators
     - Webhook / HMAC / signature / crypto verification helpers
     - HTML / template rendering & escaping helpers
     - File upload / path containment & subprocess / dynamic code (`eval`, `exec`, `spawn`, `shell=True`)
     - Mass-assignment allowlists / object-merge / validation helpers
     - Structured loggers / PII redaction & secret/env loading
   - Read **only the primitive implementations and 1–2 representative call sites** per category—never read dozens of repetitive routes or domain modules.
4. Record the current `HEAD` commit SHA via `git rev-parse HEAD` (or `"uncommitted"`).

### Step 2: Targeted Human Interview (3–5 Questions Max)
Unless the user already supplied this context in the prompt, present a **3–5 bullet summary** of what you inferred and ask *only* what code cannot reliably tell you:

1. **Exposure & upstream controls:** Where is this deployed (public internet, internal VPC/mTLS mesh, CLI/library)? What does an upstream proxy/gateway/WAF actually enforce or strip (e.g., JWT validation, identity header stripping), and what reaches this app raw?
2. **Crown jewels & Sev-0 failures:** What is the #1 catastrophic failure mode here (e.g., cross-tenant IDOR, SQLi/XSS/RCE, privilege escalation, SSRF to cloud metadata, credential/PII leakage)?
3. **Repo visibility:** Is this repository `public` or `private`?
4. **Intentional guarantees & accepted risks:** What is intentionally public, trusted upstream, or legacy-exempt so coding agents don't raise false alarms or break working architecture?

### Step 3: Write `SECURITY_CONTEXT.md` (Strict O(1) Budget)
Follow [references/schema.md](./references/schema.md) strictly:
- Include valid YAML frontmatter (`schema_version: 1`, `visibility`, `last_synced_commit`). Do NOT include `trigger_paths` in `SECURITY_CONTEXT.md` frontmatter.
- **Stay strictly O(1) (target 60–120 lines, hard cap 150 lines):**
  - **Section 2 (Trust Boundaries):** Map **architectural layers & boundary mechanisms**, NEVER individual endpoints or per-model files.
  - **Section 3 (Blessed Primitives):** Group by relevant security capability (`Use <symbol> (<path>) — NEVER <dangerous sink>`), NEVER list every domain CRUD helper.
- **Search-Backed Rule-Accuracy Self-Audit (mandatory before saving):**
  - For every `NEVER use <symbol>` or `Stop-and-Flag` restriction, run a quick search across the repo for existing call sites of `<symbol>`.
  - Scope the rule accurately to the real trust boundary (e.g., *"in user-authenticated routes"*, NOT *"in all of `src/routes/**`"* if HMAC-verified webhooks legitimately use it).
  - If legacy debt exists in a large repo, **ratchet in one line** (e.g., *"Legacy callers exist in `src/legacy/**`; NEVER introduce new calls in new code or `src/v2/**`"*). Never list every legacy call site, and never write a rule that contradicts valid existing patterns.
  - **Never legitimize bugs as "intentional":** Do NOT mark an unsafe security behavior in existing code (e.g., reflecting arbitrary `Origin` with `credentials: true`, skipping auth/ACL checks, unvalidated outbound fetches) as *"intentional / accepted"* unless explicitly confirmed by the owner or documented as a deliberate security design choice. Treat suspicious existing code as unverified debt, not blessed intent.
- **Section 4 (Stop-and-Flag Rules):** Target *security invariant violations* (weakening auth/crypto/CORS/replay checks, bypassing tenancy/path/SSRF guards, raw SQL/HTML/eval/shell injection, un-allowlisted mass assignment)—never block legitimate new features that follow Section 3's blessed primitives.
- Verify every referenced file path exists and total length is **≤ 150 lines**.

### Step 4: Wire Dynamic Trigger Pointer in `AGENTS.md`
Insert or update a compact `## Security Context` section in `AGENTS.md` (creating `AGENTS.md` if absent). Keep it **2–4 lines** regardless of repo size by using **coarse boundary globs** (≤ 10 globs) plus **intent triggers**:

```markdown
## Security Context

Read [SECURITY_CONTEXT.md](./SECURITY_CONTEXT.md) before editing `<coarse boundary globs>` — or whenever adding or modifying `<repo-specific security intents>`. Skip it for pure formatting, UI copy, docs, or non-boundary utility edits outside these paths.
```

- Do **NOT** include pure utility/formatting/docs directories in the trigger globs.
- If the repo uses `CLAUDE.md` without importing `@AGENTS.md`, also wire or offer the same pointer section there.
- Recommend protecting `SECURITY_CONTEXT.md` and `AGENTS.md` in `.github/CODEOWNERS`.

---

## Workflow: `sync` Mode (Continuous Updates)

1. Read existing `SECURITY_CONTEXT.md` and extract `last_synced_commit` from frontmatter.
2. Inspect `git diff --stat <sha>..HEAD` (or run `node <skill-dir>/scripts/detect-drift.mjs`).
3. Inspect only **structural security changes**: new/removed trust-boundary layers, new frameworks/manifests/infra, changes to auth/middleware/blessed-primitive exports, or newly introduced dangerous sinks. Ignore routine feature/business-logic edits that follow existing patterns.
4. Update minimally while keeping total length **≤ 150 lines** and preserving human-verified Section 1 invariants and Section 4 escalation rules unless a genuine trust-boundary change occurred (ask first in that case).
5. Bump `last_synced_commit` and update the `## Security Context` pointer in `AGENTS.md` only if coarse boundary paths or intents changed.

---

## Local usage (MEGAI)

Vendored from [enclave-ai/skills](https://github.com/enclave-ai/skills) @62b702f (MIT, `LICENSE`); the sections above are upstream, unchanged.

- `init` and `sync` write repo files (`SECURITY_CONTEXT.md`, the `AGENTS.md` pointer). Run them only on request, under the
  project's Brokan task, in its `task/*` worktree, and deliver like any other change. Never run them on the shared checkout.
- `check` is read-only: `node ~/.pi/agent/skills/security-context/scripts/detect-drift.mjs <repo>` (0 clean, 2 drift, 1 missing).
- Default `visibility: private` unless the owner confirms the repo is public. Keep the file free of hosts, IPs and secrets.
- Once present, `diff-security` reads it first and `megai-change-review` puts it in the independent reviewer's packet.
- Local patches in `scripts/detect-drift.mjs` (marked `MEGAI patch`): `last_synced_commit` must be a full hash or
  `uncommitted` before it reaches git; `**` globs compile correctly; unreadable history exits 1, not clean; renames
  count on both sides; CRLF frontmatter is accepted.
