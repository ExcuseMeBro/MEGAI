# Optional Laya shadow verdict for Pi

This Pi extension **only observes** eligible long, successful test-command output. It asks a locally running mu-compatible Laya sidecar whether the output is mostly repetitive passing/progress noise. It records a probability/status and timing in Pi's session entries (`megai.laya.shadow`), **not the raw output**. The original tool result, user-selected model and thinking level remain unchanged. It does not replace Headroom, accept/reject commands, remove test errors, or satisfy task acceptance.

It is **not installed by default**. No model or Python dependency is downloaded, started, or installed by this extension. To opt in for one separate Pi process, first independently start a trusted local Laya server implementing mu's `POST /evaluate` contract (default loopback port 47823); then from this repository run:

```sh
MEGAI_LAYA_SHADOW=1 pi --extension "$(pwd)/pi-skill/laya-shadow/index.ts"
```

`MEGAI_LAYA_SHADOW_PORT` may select another numeric loopback port. The destination is fixed to `127.0.0.1`; no provider key, HTTP proxy or redirect is used. The server receives a **bounded sample** (up to 900 characters) of the test output, which can still contain sensitive material; opt in only to a trusted local server. Only commands beginning with `npm test`, `npm run test`, `node --test`, `pytest`, or `python -m pytest/unittest` are eligible when output has at least 1024 characters. No output or verdict is forwarded to a hosted **judge** by this extension; Pi still sends its normal tool result to the user-selected main model as before. If the server is absent, slow or answers incorrectly, Pi keeps working unchanged and records `unavailable` metadata. `shadow` never acts on a verdict; a `noise` status is **not** permission to suppress a test result.

Verify with `bash tests/pi-laya-shadow.sh`. This uses the installed Pi extension loader and a loopback mock endpoint; it does **not** prove that a real Laya model is installed or that its classifications are accurate. Compare actual ledger entries with human-labelled outcomes before considering an active feature. Do not run this against secret-bearing logs without a privacy review.
