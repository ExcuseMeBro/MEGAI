---
name: sim-guard
description: Guardrails for agents that use iOS simulators so parallel agents don't overload the Mac. Use before any session boots, builds to, runs on, taps through or screenshots an iOS simulator (xcodebuild, simctl, Expo/EAS run:ios, Xcode or simulator MCP tools, Maestro), and when the Mac is hot, slow or out of memory.
---

# sim-guard

A stock iOS simulator idles at about 3.5 GB and 130+ processes; a slim pool sim uses about 0.4 GB. These rules keep
every agent (Pi, Codex, Claude) on a small shared pool of dedicated, slimmed sims.

The command is `sim-guard` (`~/.local/bin/sim-guard`). It needs Xcode and `simslim`.
Adapted from [annayal-consumerxai/sim-guard](https://github.com/annayal-consumerxai/sim-guard) (MIT).

## First time on a machine

`sim-guard init` creates (or reuses) dedicated sims named `sim-guard-1` and `sim-guard-2` on the newest iOS runtime,
writes them to `~/.config/sim-guard/pool` and slims them. It never adopts an existing simulator: sims the user made
by hand are not in the pool and are never wiped. StoreKit, push and universal links stay on.

## Rules for every agent

1. **Preflight first.** Before building to or booting a simulator, run `sim-guard preflight`. Exit 1 means blocked:
   don't boot anything.
2. **Hard cap of 2 booted sims machine-wide** (`SIM_CAP`), and no boot when Mac free memory is under 25%. When
   blocked, wait, reuse a pool sim you already hold, or ask the user. Never boot a third. Heavy builds still follow
   the "one heavy job on this Mac" rule.
3. **Use the pool, never create sims.** `sim-guard acquire` boots a free pool sim and prints `ACQUIRED <udid>`. Pass
   that UDID everywhere: `xcodebuild -destination id=<udid>`, `npx expo run:ios --device <udid>`, simulator MCP tools.
   Never `simctl create`, clone or `simctl erase` a sim for a task (erase can drop the slim profile). Acquire is
   locked across agents, so two agents never get the same sim.
4. **Release after every run.** `sim-guard release <udid>` removes user-installed apps, resets the keychain, shuts the
   sim down and drops your lease. Add `--keep-apps` only when the user wants to keep using the app. It refuses any
   UDID outside the pool.
5. **Orphans.** A booted sim outside the pool is an orphan; it may be the user's own sim. `audit` prints the shutdown
   command. Don't run it without asking the user.
6. **One agent per sim.** Two agents tapping the same sim corrupt each other's runs. `audit` shows each pool sim's
   lease (owner and since when).

## Auditing

`sim-guard audit` lists every booted sim with UDID, name, runtime, RAM, CPU, slim state and pool lease or orphan, plus
Mac free memory. `simslim top` is the live view. Orchestrators run `audit` between waves and hold the next wave
while `preflight` is blocked.
