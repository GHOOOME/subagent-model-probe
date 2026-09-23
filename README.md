# subagent-model-probe

An Agent Skill that stops an AI coding agent from trusting a stale "which models can run
subagents?" list — and makes it **probe instead of assume**.

## The problem it solves

When an agent fans out work to subagents, it has to choose which models to spawn. It is very
tempting — and very wrong — to answer that from a table the agent remembers, or from a note a
previous session left behind.

Subagent capability is a **per-model, server-side account entitlement**:

- It is **per model**, not per vendor. One model from a family can work while its sibling is
  refused.
- It is **not visible in local config** and **cannot be enabled from the client**.
- **Providers change it over time.** A list that was true last month is a guess today.

So a capability table *always* decays into misinformation. The failure mode is subtle and
expensive: the agent reports "model X can't run subagents" with total confidence, based on
nothing it actually tested, and the user has no way to tell.

The real-world incident that produced this skill:

> An agent read a cached table saying that three model families "don't support subagents", and
> repeated it to the user as if verified. Actual probing showed capability **is** available in two
> of those families — on their **newer** models — while older models in the same families were
> genuinely refused. The table was wrong in both directions, and the agent had presented it as fact.

## What the skill makes an agent do

1. Treat **every** capability list (including any table inside the skill itself) as a **dated hint,
   never a fact**.
2. **Probe before fan-out** — spawn one trivial probe per model you intend to use.
3. Recognize the **two distinct error signatures** and what each one means.
4. Tell a **weak (toy) probe** from a **strong (real-task) probe** — a "reply OK" probe proves the
   model can start and return text; it proves *nothing* about file reads or tool use.
5. **Record results into a dated matrix** so the next session starts warmer than this one did.
6. Report honestly: if a model was not probed, say **"unverified"**.

## Files

| File | Purpose |
|---|---|
| `SKILL.md` | The skill itself — probe procedure, error signatures, matrix format |
| `scripts/record_capability.py` | Record a probe result into a dated JSON matrix; `--show` renders it as Markdown |
| `scripts/check_matrix.py` | Pre-flight gate before a fan-out — **fails closed** unless every requested model is freshly verified |
| `agents/openai.yaml` | UI metadata (display name, short description) |
| `examples/example-capability-matrix.json` | A real, dated example matrix (see the note below) |

## Install

Standard-library Python only — no dependencies.

```bash
git clone https://github.com/GHOOOME/subagent-model-probe.git
mkdir -p ~/.codex/skills/subagent-model-probe
cp -R subagent-model-probe/SKILL.md \
      subagent-model-probe/scripts \
      subagent-model-probe/agents \
      ~/.codex/skills/subagent-model-probe/
chmod +x ~/.codex/skills/subagent-model-probe/scripts/*.py
```

The skill is picked up on the next turn. To install for a different agent that reads skills from a
directory, copy the same three items into that skills directory instead.

## Usage

### Before a fan-out: check the matrix

```bash
python3 scripts/check_matrix.py --store ./matrix.json --models model-a model-b
```

Output is one line per model plus a verdict:

```
model-a → works (tested 2026-09-23)
model-b → NO-CAPABILITY (tested 2026-09-23)

PROBE FIRST: model-b no-capability
```

Exit code **0** only when every requested model is verified `works` **and** fresh (default: within
90 days). Otherwise **1**. It fails closed on purpose — an unclear answer is not a green light.

### Record a probe result

```bash
# after probing a model
python3 scripts/record_capability.py --store ./matrix.json \
    --model model-a --result works --note "also passed a real file-read probe"

# see the matrix, newest first, with stale rows flagged
python3 scripts/record_capability.py --store ./matrix.json --show
```

`--result` accepts `works`, `no-capability`, `metadata-error`, `timeout`, `other`.
Re-recording the same model updates `last_tested` and keeps `first_tested`.

Use `--max-age-days N` to tighten or loosen the freshness window in `check_matrix.py`.

## The two error signatures

| Signature | Meaning | Action |
|---|---|---|
| `400 InternalError.Algo.InvalidParameter: Agent capabilities are not enabled for the current model` | The account is **not entitled** to run subagents on this model. Deterministic — not transient, not your request's fault. | Record `no-capability`. Do not retry. |
| `500 InternalError.Algo: 'agent_api_metadata'` | A **different** failure: the server has no agent-API metadata for this model, so the spawn never reached the entitlement check. | Retry **once** (it is a 5xx). If it repeats, record `metadata-error`. |

Anything else — another 4xx/5xx, a timeout, an empty reply — is recorded as-is. That is
**unknown**, not *incapable*.

## Why the example matrix is only an example

`examples/example-capability-matrix.json` contains real probe results from one account on one day.
Model entitlements differ per account, per gateway, and over time. **Read it as a dated hint about
which models are worth probing first — never as a statement about your account.**

That is the entire thesis of this skill, applied to itself.

## License

MIT — see [LICENSE](LICENSE).
