# MEGAI subagent model policy

Every delegated scout, worker, debugger and reviewer uses the **Pi harness** and
exactly one of these models, including from local Pi sessions:

- `openai-codex/gpt-6-astra` — orchestration or exceptionally complex work, high.
- `openai-codex/gpt-5.6-luna` — bounded discovery, medium; scoped edits, high.
- `openai-codex/gpt-5.6-terra` — core implementation, high.
- `openai-codex/gpt-5.6-sol` — complex debugging and independent review, high.

Use only explicit medium/high thinking. Pick within this list; older GPT models,
other providers, aliases, wildcards and automatic model fallback are not allowed.
Unavailable approved models are a blocker, not permission to substitute.
The user's current parent model, credentials and provider catalog stay unchanged.

Use structured Paseo `create_agent`: `provider: "pi/openai-codex/gpt-5.6-luna"`,
`settings: { thinkingOptionId: "high" }`. First send only a neutral READY prompt;
verify returned harness **pi**, exact model and effective thinking via agent status
before sending task context. On mismatch cancel the child and report the blocker.
Re-check restored/existing agents before reuse. Children never delegate or mutate
Plane. Writers use managed isolated worktrees; direct parent tools suffice for
bounded work. Main promotion still needs separate explicit approval.

The local Pi `megai-model-guard` extension blocks unsupported/missing models and
thinking on structured Paseo creation, rejects out-of-list model updates and
blocks native subagent tools, opaque `mcpScript` calls and scheduled delegation.
Use individual structured MCP calls instead. Recognized CLI agent launches are
redirected to that path with an error, not silently rewritten. This is a tool-call
safety guard, **not an OS sandbox**: arbitrary shell scripts, external Paseo/UI
clients, disabled extensions and already-running children are outside its boundary.
Do not route around the guard. Reload local Pi after installation; if resource
filters exclude the guard, report the blocker rather than claim enforcement.
