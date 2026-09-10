# Capy additions

The persistent `capy` branch holds Capy-specific MEGAI adaptations. It starts from
`dev` at `f825f52a2a6bd4e48e87eb092571746423632e7f`. Changes here are not automatically
merged into `dev` or `main`.

## Current support

This is a **manual instructions pack**, not a Capy installer or native extension.
The user confirmed Plane MCP can list projects in Capy. Instruction loading,
worktree support, review automation and runtime tool integration have not been
verified in Capy. Existing MEGAI launchers and installers remain unchanged;
`megai capy` is not implemented.

- [instructions.md](instructions.md): portable acceptance-first workflow, Plane
  boundaries, isolated writes, verification and review handoff.
- [benchmark/README.md](benchmark/README.md): proposed isolated Astra/high
  comparison protocol; approve its public interfaces before implementing tests.
- Add future Capy-specific documents and adapters under this directory. Keep
  shared runtime changes separate until their compatibility is tested and their
  delivery explicitly approved. Execution status stays in Plane, not a local board.

## Manual use

1. Select the MEGAI repository's `capy` branch when working on these additions.
2. Supply [instructions.md](instructions.md) through an instruction mechanism
   actually supported by your Capy version, or paste it into the task prompt.
   Do not assume Capy auto-loads this filename. Preserve existing instructions.
3. Keep the already-working Plane MCP connection targeting `brodev`. This pack
   neither copies tokens nor changes MCP settings. Use private credentials and
   the narrowest access scope your client supports.
4. Ask Capy to identify the applicable workflow and delivery branch, then list
   `brodev` projects read-only. Confirm that it reports `capy` for MEGAI Capy work
   and uses the real Plane tool rather than inventing a result.
5. On a separately authorized small change, verify that Capy starts/reuses one
   Plane item before edits, provides real test evidence, and hands off at
   `In Review` without marking `Done` or merging into another branch. This smoke
   test creates real task/repository data; it has not been run by this pack's author.

Remove the supplied instruction text to stop using the pack; existing Plane
items, credentials and repository changes remain intact.

## Local documentation checks

From the `capy` checkout:

```bash
git diff --check
git diff --name-only dev...HEAD
```

Review local Markdown links and ensure this initial change touches only this
folder and its root README pointer. These checks verify the artifact, not Capy
runtime behavior. Measure time, token usage and acceptance failures on comparable
work before asserting efficiency improvements.
