# Caveman core default

Caveman core installation/reuse now defaults on. Existing core content is preserved; missing core is copied from the pinned installer package without invoking its all-agent installer, force-wiring, hooks or companion workflows. Package acquisition retains the existing v2.2.0 pin and disables npm lifecycle scripts.

Pi wiring explicitly includes only `~/.agents/skills/caveman/SKILL.md`, after lean exclusions including `!*`. Companion Caveman skills, Cavecrew and the legacy OMP orchestrator remain excluded. Repeated wiring is idempotent. `MEGAI_CAVEMAN=0 megai wire pi` removes the managed core inclusion; the same flag skips installation without deleting files. User-provided unrelated filters/settings are retained.

When core is enabled, chat defaults to Caveman full unless the user requests normal mode. User language, uncertainty, technical meaning and safety warnings remain intact; persisted artifacts use normal prose. Models, providers, permissions and validation gates do not change.

`tests/caveman-default.sh` exercises the actual installer/profile function with opt-out, default core copy, existing user content, no upstream invocation, repeat wiring, lean filters and preserved settings/state. `tests/pi-runtime.sh` covers runtime/legacy settings compatibility. The real installed Pi resource loader confirmed exactly one `caveman` skill, no `caveman-*` or `cavecrew` companions and no diagnostics. This is activation evidence, not a measured token-saving or speed claim.

Private local backup: `~/.megai-config-backups/caveman-default-20260907T164107Z/`. Local state changed only for Caveman; settings changed only in skill selection, alongside the targeted response-style condition and managed MEGAI guidance. Provider/model/package settings were verified unchanged. Reload or start a fresh Pi session to replace old cached discovery.
