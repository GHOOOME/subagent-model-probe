# Installing this skill for your agent

The skill is portable: one `SKILL.md` plus two dependency-free Python scripts. Any agent that
reads a `skills/` directory can use it.

## What gets copied

```
SKILL.md        the skill itself
scripts/        record_capability.py, check_matrix.py
agents/         UI metadata (Codex-style; safe to ignore elsewhere)
```

## Codex

```bash
git clone https://github.com/GHOOOME/subagent-model-probe.git
mkdir -p ~/.codex/skills/subagent-model-probe
cp -R subagent-model-probe/{SKILL.md,scripts,agents} ~/.codex/skills/subagent-model-probe/
chmod +x ~/.codex/skills/subagent-model-probe/scripts/*.py
```

Available on the next turn. Invoke implicitly (the description decides) or explicitly with
`$subagent-model-probe`.

## Claude Code

```bash
mkdir -p ~/.claude/skills/subagent-model-probe
cp -R subagent-model-probe/{SKILL.md,scripts} ~/.claude/skills/subagent-model-probe/
```

Use `~/.claude/skills/` for all your projects, or `.claude/skills/` inside one project to scope it.
Claude reads the `name` and `description` from the frontmatter to decide when the skill applies; you
can also invoke it directly by name.

> `agents/openai.yaml` is Codex-specific UI metadata. Copying it is harmless; other agents ignore it.

## Cursor

```bash
mkdir -p ~/.cursor/skills/subagent-model-probe
cp -R subagent-model-probe/{SKILL.md,scripts} ~/.cursor/skills/subagent-model-probe/
```

## Gemini CLI

```bash
mkdir -p ~/.gemini/skills/subagent-model-probe
cp -R subagent-model-probe/{SKILL.md,scripts} ~/.gemini/skills/subagent-model-probe/
```

## opencode

```bash
mkdir -p ~/.config/opencode/skills/subagent-model-probe
cp -R subagent-model-probe/{SKILL.md,scripts} ~/.config/opencode/skills/subagent-model-probe/
```

## Several agents at once (shared canonical dir)

If you use multiple agents, keep **one** canonical copy and symlink it into each agent's directory.
This is the pattern already used on many machines, and it means you update the skill in one place:

```bash
git clone https://github.com/GHOOOME/subagent-model-probe.git
mkdir -p ~/.agents/skills/subagent-model-probe
cp -R subagent-model-probe/{SKILL.md,scripts,agents} ~/.agents/skills/subagent-model-probe/

# then symlink into each agent that supports it
mkdir -p ~/.claude/skills ~/.cursor/skills ~/.gemini/skills
ln -sfn ~/.agents/skills/subagent-model-probe ~/.claude/skills/subagent-model-probe
ln -sfn ~/.agents/skills/subagent-model-probe ~/.cursor/skills/subagent-model-probe
ln -sfn ~/.agents/skills/subagent-model-probe ~/.gemini/skills/subagent-model-probe
mkdir -p ~/.config/opencode/skills
ln -sfn ~/.agents/skills/subagent-model-probe ~/.config/opencode/skills/subagent-model-probe
```

Why symlinks: one copy to update, and no risk of the copies drifting apart.

## Verify the install

```bash
SK=~/.claude/skills/subagent-model-probe      # or wherever you put it
python3 "$SK/scripts/check_matrix.py" --models probe-model
# → probe-model → UNTESTED  /  PROBE FIRST: ...   (exit 1 — correct, nothing probed yet)
```

A `PROBE FIRST` verdict on a fresh install is the skill working as intended. It fails closed.

## Requirements

`python3` only — standard library, no packages, no network access. Works on macOS and Linux.

## If your agent is not listed

The rule is general: find the directory your agent loads skills from, and create a folder there
containing `SKILL.md` (and copy `scripts/` next to it). The frontmatter `name` + `description` are
what make the agent pick it up automatically.
