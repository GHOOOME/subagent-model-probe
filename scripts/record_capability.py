#!/usr/bin/env python3
"""Maintain a dated subagent capability matrix (JSON) and print a Markdown table.

A row is a dated hint recorded from a past probe; only a fresh probe is proof.
Never rely on the matrix alone for a fan-out decision — always re-probe stale rows.
"""

import argparse, json, sys, os
from datetime import date, timedelta

VALID = {"works", "no-capability", "metadata-error", "timeout", "other"}


DEFAULT_STORE = os.path.expanduser(
    os.environ.get("SUBAGENT_PROBE_STORE", "~/.subagent-model-probe/capability-matrix.json")
)


def _load(path):
    if not os.path.exists(path):
        return {}, None
    try:
        with open(path) as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"Cannot read {path}: {exc}"
    if not isinstance(data, dict):
        return None, f"{path} does not contain a JSON object"
    # Every entry must itself be an object; a wrongly-shaped store must fail
    # closed with a clear message rather than crashing later in _show().
    for model, entry in data.items():
        if not isinstance(entry, dict):
            return None, (
                f"{path} is malformed: entry for {model!r} is "
                f"{type(entry).__name__}, expected an object"
            )
    return data, None


def _save(path, data):
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w") as fh:
        json.dump(data, fh, indent=2)


def _show(data):
    if not data:
        print("*(no entries)*")
        return
    rows = sorted(data.items(), key=lambda kv: kv[1].get("last_tested", ""), reverse=True)
    print("| # | Model | Result | First Tested | Last Tested | Notes |")
    print("|---|-------|--------|-------------|------------|-------|")
    cutoff = date.today() - timedelta(days=90)
    any_stale = False
    for i, (model, e) in enumerate(rows, 1):
        last = e.get("last_tested", "?")
        ld = date.fromisoformat(last) if last != "?" else None
        stale = ""
        if ld and ld < cutoff:
            stale = " ⚠️ stale"
            any_stale = True
        print(f"| {i} | `{model}` | {e.get('result','?')}{stale} "
              f"| {e.get('first_tested','?')} | {last} | {e.get('notes','')} |")
    print(f"\n**Last updated:** {date.today().isoformat()}")
    if any_stale:
        print("\n⚠️  **This table is a hint, not proof.** "
              "Rows marked stale must be **re-probed** before relying on them. "
              "Even fresh rows are dated observations — server-side entitlements change.")


def main():
    p = argparse.ArgumentParser(
        description="Record or display subagent model capability probes.")
    p.add_argument("--store", default=DEFAULT_STORE,
                   help=f"Path to the JSON store (default: {DEFAULT_STORE})")
    p.add_argument("--model", help="Model identifier to record")
    p.add_argument("--result", choices=sorted(VALID),
                   help="Capability probe result")
    p.add_argument("--note", default="", help="Optional free-text note")
    p.add_argument("--date", help="Test date YYYY-MM-DD (default: today UTC)")
    p.add_argument("--show", action="store_true",
                   help="Print Markdown table and exit")
    args = p.parse_args()

    if args.show:
        if args.model or args.result or args.date:
            print("Usage: record_capability.py --store PATH --show", file=sys.stderr)
            sys.exit(1)
        data, err = _load(args.store)
        if err:
            print(err, file=sys.stderr)
            sys.exit(2)
        _show(data)
        sys.exit(0)

    if not args.model or not args.result:
        print("Usage: record_capability.py --store PATH --model NAME --result RESULT "
              "[--note TEXT] [--date YYYY-MM-DD]", file=sys.stderr)
        sys.exit(1)

    data, err = _load(args.store)
    if err:
        print(err, file=sys.stderr)
        sys.exit(2)

    test_date = args.date or date.today().isoformat()
    try:
        date.fromisoformat(test_date)
    except ValueError:
        print(f"Invalid date '{test_date}' — use YYYY-MM-DD", file=sys.stderr)
        sys.exit(1)

    prev = data.get(args.model)
    first = prev["first_tested"] if prev else test_date
    data[args.model] = {
        "result": args.result, "first_tested": first,
        "last_tested": test_date, "notes": args.note,
    }
    _save(args.store, data)
    print(f"Recorded {args.model} → {args.result} (tested {test_date})")


if __name__ == "__main__":
    main()
