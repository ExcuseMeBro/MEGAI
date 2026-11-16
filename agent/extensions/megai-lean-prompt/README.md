# MEGAI lean prompt

Pi lists every skill (name, full description, path) in the system prompt on every
model request. With ~90 skills that was ~58k chars, ~75% of the prompt, while
sessions loaded about ten of them. On `before_agent_start` this extension keeps the
full entry only for the skills in `config.json` `full` and lists the rest as one
`name: trigger` line under a shared path (`<skill_catalog>`).

Measured on the same prompt (gpt-6.1-sol): system prompt 77.7k → 36k chars, input
tokens per request 23,767 → 13,501 (−43%). Routing still works: the model found and
read compacted skills (`eas-update`, `ask-sonner`) from the catalog.

- Only the per-run copy of the prompt options changes: skill files, the registry and
  `/skill:name` commands are untouched. Without a `read`/`bash` tool it does nothing.
- `full`: skills that keep their full description (frequent or always-relevant ones).
  `limit`: trigger length. `minSkills`: below this many compactable skills, no-op.
- `MEGAI_LEAN_PROMPT=0` disables it. Errors fail open (default listing stays).
