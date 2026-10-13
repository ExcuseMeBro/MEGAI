# Explicit queue repin after approved history reconciliation

Default reconcile still rejects an unknown target head. `repin` is an explicit
administrative reconciliation, not delivery, task acceptance or permission to
change Git history. Use only after separately approved head reconciliation, with
the old writer stopped and all task resources preserved.

```
megai queue reconcile --id REQUEST --outcome repin --owner-stopped \
  --acknowledge-head-change --evidence /absolute/receipt.txt \
  --request /absolute/reviewed-vector.json \
  --preserved-ref /absolute/repository refs/heads/preservation/before-reconcile
```

The receipt must record actual approval, observed before/after heads, ownership,
remaining work and uncertain mutations. The replacement vector must keep the
same request/Plane/project/repository/branch/resource/dependency identity. Only
held or expired pre-delivery reservations (`candidate_head == expected_head`)
can repin. An independent local branch must preserve the exact old head for each
repository; every new pin must match the actual clean, idle target. Dirty/busy
checkouts and changed project identities still block. No Git writes occur.

Success retains FIFO sequence, journals the old/new vectors, evidence digest,
previous recovery and preservation refs, then returns the request to queued.
Old owner/token are fenced; claim a fresh grant before further writes. Actual
candidate delivery must use existing delivery reconciliation, never repin.
