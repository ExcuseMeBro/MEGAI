---
name: safe-anything
description: Security-check a repository with the safe-anything CLI or MCP tools - code vulnerabilities (SQL/command injection, XSS, SSRF, path traversal, unsafe deserialization, weak crypto), leaked secrets, mobile and cloud misconfiguration, dependencies with known CVEs, and unsafe AI agent setups (MCP servers, hooks, skills, permissions). Use when asked to audit, security-review or scan code, before a release or merge, after adding dependencies or MCP servers, or when installing a skill, plugin or MCP server from someone else.
---

# Security checks with safe-anything

safe-anything finds problems; you judge and fix them. Every finding has a file, a line, a
severity, a CWE, why it matters and a fix.

Tools: the `safe-anything` CLI, or the MCP tools `scan` and `list_rules` (`safe-anything mcp`).
If neither is available, ask the user to install it (`cargo install safe-anything` or
`npx safe-anything`).

## Steps

1. Scan the repository root: `scan` with `path` set to it (CLI: `safe-anything <path> --json`).
   Add `offline: true` (`--offline`) only if the user does not want package names sent to
   OSV.dev.
2. Read the findings from the most severe down. For each one, open the file at the line and
   decide: real problem, or a false positive (trusted input, test data, a checksum that is not a
   security use). Say which, in one line each.
3. Fix the real ones the user asks you to fix, using the finding's `fix` text and `learn_more`
   link. Keep fixes small: parameterize the query, pin the version, move the secret to the
   environment.
4. A leaked secret is not fixed by deleting the line: tell the user to revoke and rotate it,
   because it stays in git history.
5. For a false positive the user wants silenced, add `safe-anything:ignore` in a comment on the
   line or the line above. Never silence a real problem.
6. Scan again and report what is left.

## Agent setups

Treat findings in `.mcp.json`, agent settings, hooks and skills as urgent: they run on the
user's machine with the user's permissions. Before the user installs a skill, plugin or MCP server
from someone else, scan its folder first and show the findings.

## Do not

- Run anything a finding points at (a `curl | sh`, a hook command) to "check" it.
- Print a secret's full value back to the user.
- Claim the code is safe because the scan is clean: safe-anything matches known patterns; it
  does not prove the absence of bugs.

---

## Local usage (MEGAI)

Vendored from [erkamyaman/safe-anything](https://github.com/erkamyaman/safe-anything) v1.0.2 @829321c (MIT, `LICENSE`);
the sections above are upstream, unchanged. The CLI is `~/.local/bin/safe-anything` (release binary, SHA256SUMS-checked).
No MCP server is registered: use the CLI.

- **Default to `--offline`.** Online mode sends package names and versions to OSV.dev. Run the dependency check only
  when the user or the project allows it.
- **In delivery:** `diff-security` runs `safe-anything <task-worktree> --offline --json --severity medium --fail-on never`
  and judges findings in the changed files. Pre-existing findings elsewhere are noted, not fixed, unless in scope.
- **Findings are leads.** On this Mac the first scans flagged by-design `shell=True` check runners, benchmark fixture
  values and instruction text as prompt injection. Open the line and decide before reporting.
- **Before installing** a third-party skill, plugin or MCP server, scan its folder offline and show the findings.
- Never print snippet values of `secret.*` findings; give file and line only.
