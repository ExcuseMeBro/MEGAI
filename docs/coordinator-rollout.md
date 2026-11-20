# Coordinator rollout pilot

The pilot models one Coordinator and an allowlist of local workers. It is an
opt-in CLI run from the checkout, not an OpenBot routine, installer, or network
service. Workers are directories in a private system temporary directory. The
four synthetic components stand in for Pi runtime, skills, plugins, and managed
configuration; they are plain text markers, not executable packages. No existing
Pi or OpenBot settings, sessions, credentials, or accounts are used.

## Run a local pilot

Use Python 3.11+ on a POSIX host. Run the commands from the MEGAI checkout:

```sh
python3 -I -B lib/coordinator_rollout.py init --canary canary \
  --follower worker-a --follower worker-b --follower worker-c --max-parallel 2
```

Set `SANDBOX` to the exact `sandbox` path printed by `init`. The worker list and
concurrency limit are fixed at initialization (2–32 workers, concurrency 1–8).

```sh
python3 -I -B lib/coordinator_rollout.py bundle --sandbox "$SANDBOX" --version v1
```

Set `SHA` to the printed `sha256`. Start the rollout, then inspect it from a
separate invocation:

```sh
python3 -I -B lib/coordinator_rollout.py rollout --sandbox "$SANDBOX" --bundle v1 --sha256 "$SHA"
python3 -I -B lib/coordinator_rollout.py status --sandbox "$SANDBOX"
```

Repeat with `v2` and its digest to roll out a second version. A version and digest
pair always returns its recorded outcome after it has finished, without another
rollout. A different digest for an already-used version is rejected. Bundles are
limited to the exact four synthetic markers for their version. SHA-256 checks
that the manifest has the expected bytes; it is not release signing.

## Failure and recovery

The canary is staged, activated and checked before any follower starts. Followers
run in bounded waves; a wave's releases must all stage before its activation.
The atomic `state.json` journal is the activation source of truth. It points to
immutable-by-protocol release directories, and stores per-worker progress, the
previous activation map and the outcome. One writer can mutate a sandbox; a
separate `status` call can inspect progress throughout the run.

A staging or health failure stops unscheduled waves and restores the previous
activation map, including any earlier successful wave. Staged candidate files
remain in the sandbox for inspection; a staged file does not imply activation.
If a process stops mid-run, `status` shows `pending` and new rollouts refuse to
start until an operator explicitly restores the previous map:

```sh
python3 -I -B lib/coordinator_rollout.py recover --sandbox "$SANDBOX"
```

`rollout` exits `0` for a successful outcome, `1` for a failed/interrupted recorded
outcome, and `2` on rejected input or an unavailable writer. Sandboxes are local
and disposable; they are not automatically removed and must not store anything
valuable. Do not edit the journal or stage files in place. The sandbox protects
against out-of-scope CLI inputs and is not a security boundary against other
programs running as the same OS user.

This is **not a multi-PC deployment**. There is no network registration or
transport, SSH, real Pi installation, scheduler, or OS-specific worker adapter.
Before a real fleet rollout, verify approved per-host enrollment and identity,
signed artifacts and trust policy, isolated host permissions, real per-OS health
checks, and rollback on canary hosts. Keep credentials and sessions outside any
managed payload.
