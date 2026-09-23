---
name: subagent-model-probe
description: Probe models for subagent capability before any fan-out, and treat every cached capability table as a dated hint instead of a fact. Use when choosing models to spawn subagents/parallel agents, or when a spawn fails with "Agent capabilities are not enabled for the current model" or an 'agent_api_metadata' error. Not for general model selection, pricing, benchmarks, or quality comparison.
---

# Subagent Model Probe

Subagent capability is a **server-side, per-model account entitlement**. It is not a vendor
property, it is not visible in local config, it cannot be enabled from the client, and providers
change it over time. Therefore:

> **Any capability table you already have — including the example in this file — is a dated hint.
> It is never a fact. Never repeat a hint to the user as if it were tested.**

Hints are useful only for *ordering* which models to probe first. They are never a substitute for
a probe, and never a justification to skip one.

## When to use

- You are about to spawn one or more subagents and must choose a model.
- A spawn failed with a capability or metadata error and you need to know what it means.
- You are asked "which models can run subagents?" and your only source is a table or memory.
- You are about to write or update a capability matrix.

## When not to use

- Single-agent work with no delegation — nothing to probe.
- Choosing a model for quality, cost, context length, or reasoning effort. Capability gating is a
  separate question; a model can be excellent and still refuse to spawn.
- The platform exposes a supported capability-introspection API. Call it, and still probe once.
- You already probed this exact model, on this account, in this session. Reuse the result and say
  when it was measured.

## Probe procedure (mandatory before fan-out)

**Do not skip this. Do not shorten it. Do not substitute a hint for it.**

1. **List the candidate models** you might fan out to. Cap the list — probing is cheap but not free.
2. **Spawn one probe per candidate, all in parallel.** Probes are independent; never chain them
   serially behind long waits.
3. **Toy probe shape** (sufficient only to answer "can it start and return text"):

   ```text
   model:          <candidate>
   effort:         lowest available
   prompt:         "Reply with exactly PROBE_OK and nothing else. Do not use tools."
   wait cap:       60s
   ```

4. **Record the outcome verbatim** — result, error string, and wall-clock — into the matrix before
   doing anything else with it. A probe you did not write down is a probe you did not run.
5. **Only then fan out**, using models that returned a clean pass on the probe kind your task needs.

Cost discipline: one probe per model per session. A confirmed
`capabilities are not enabled` verdict is permanent for the session — do not retry it, and do not
look for a client-side workaround, because there is none.

## The two failure signatures

| Signature | Meaning | Action |
| --- | --- | --- |
| `400 InternalError.Algo.InvalidParameter: Agent capabilities are not enabled for the current model` | The account is **not entitled** to run subagents on this exact model. Deterministic, not transient, not your request's fault. | Mark `not-capable (400 entitlement)`. Do not retry. Pick a different model. |
| `500 InternalError.Algo: 'agent_api_metadata'` | A **different failure class**: the server has no agent-API metadata for this model, so the spawn never reached the entitlement check. Usually means the model is not wired for the agent API on this account/gateway. | Retry **once** (it is a 5xx). If it repeats, mark `not-capable (500 metadata)` and move on. |

Two traps:

- A 400 that names *capabilities* is not a malformed-request error. If your spawn arguments were
  wrong, the message names the parameter. Do not "fix" your prompt and re-run a capability 400.
- Anything that is **not** a clean pass and **not** one of the two signatures — other 4xx/5xx,
  timeout, empty reply, malformed output — is recorded as `error:<code>` or `timeout`. That is
  *unknown*, not *incapable*. Do not collapse unknown into `no`.

## Weak probe vs strong probe

A probe only proves what it exercises.

**Weak (toy) probe** — "reply PROBE_OK", no tools, no files. Proves: the model can be spawned as an
agent and can return text. Proves **nothing** about file reads, shell execution, tool calls, long
context, or sustained multi-step work. A model that passes a toy probe can still fail every real
subtask you hand it.

**Strong probe** — exercises the actual capability the fan-out depends on, and asks for a value the
model cannot guess, recall, or hallucinate.

Required whenever the subagents will do more than emit prose:

- **File reads** → have the probe read a specific path and report a value only present in the file
  (a nonce you wrote there, a line count, a checksum).
- **Shell / tool execution** → have it run a command and report output that is unpredictable in
  advance (current UTC timestamp, `wc -c` of a named file, a random nonce's hash).
- **Long-context or multi-step work** → give a probe with the real shape: several files, a
  constraint to satisfy, and a required output format.
- **A specific reasoning effort** → probe at that effort; effort levels are gated independently.

Rule: **record the probe kind with the result.** `capable` with no probe kind is meaningless, and
`capable (toy)` must never be used to justify a fan-out that needs tools.

## Dated matrix format

Keep one matrix per account/gateway, in your agent notes. Every row is either *verified* (has a
date, a probe kind, and an evidence pointer) or explicitly labelled `hint`.

```markdown
## Capability matrix — account: <acct-id>, gateway: <endpoint-label>
Last probed: <YYYY-MM-DD HH:MM UTC>

| Model ID | Status | Probe kind | Error signature | Date (UTC) | Evidence |
| --- | --- | --- | --- | --- | --- |
| model-a-1.0 | capable | tool (file+nonce) | — | 2026-09-23 06:10 | notes/probes/2026-09-23.md#a1 |
| model-b-2.0 | not-capable | toy | 400 entitlement | 2026-09-23 06:10 | notes/probes/2026-09-23.md#b2 |
| model-c-3.0 | not-capable | toy | 500 agent_api_metadata (x2) | 2026-09-23 06:11 | notes/probes/2026-09-23.md#c3 |
| model-d-4.0 | timeout | toy | — | 2026-09-23 06:11 | notes/probes/2026-09-23.md#d4 |
| model-e-5.0 | hint: likely capable | none | — | unverified | inherited table 2026-08-02 |
```

Rules for the matrix:

- `Status` vocabulary: `capable`, `not-capable`, `error:<code>`, `timeout`, `hint: …`,
  `unverified`. Nothing else, and `hint`/`unverified` rows never carry a probe date.
- Always store the account and gateway with the date. Capability is per-account: a matrix from
  another account, team, or provider is a hint, not a result.
- Re-probe when the matrix is older than your fan-out's blast radius — anything more than a few
  days old, or written before a provider release, is a hint. Downgrade stale `capable` rows to
  `hint: was capable on <date>` rather than deleting them; the history is the useful part.
- A useful prior, not a rule: newer model revisions have more often been entitled than older ones,
  and capability is decided per model rather than per vendor or family. Use this to order probes.
  Never use it to skip one, and never infer a sibling model's status from a relative's.

## What to report back

Report the probe, not your priors.

- The models you actually probed, when (UTC), with which probe kind, and the result — including
  verbatim error signatures for failures.
- **Explicit `unverified`** for every model you did not probe. If a row came from a table, say so
  and give that table's date.
- Which model(s) you will fan out to, and whether the probe kind matches what the subtasks need.
  If you only ran toy probes, say plainly that tool and file access are unproven.
- One line noting that this is an account-level entitlement that providers change, so the result
  carries its date.

Never state or imply that a cached row was tested this session. If you did not probe it, the answer
is "unverified".
