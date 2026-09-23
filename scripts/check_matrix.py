#!/usr/bin/env python3
"""Pre-flight guard: check a capability matrix before fan-out.

A matrix row is a dated hint; only a fresh probe is proof.
Exit 0 = every model works & fresh → SAFE.  Exit 1 = any gap → PROBE FIRST.
"""

import argparse, json, sys, os
from datetime import date, timedelta


def _load(store_path: str):
    if not os.path.exists(store_path):
        return {}
    try:
        with open(store_path, "r") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Cannot read {store_path}: {exc}", file=sys.stderr)
        sys.exit(2)


DEFAULT_STORE = os.path.expanduser(
    os.environ.get("SUBAGENT_PROBE_STORE", "~/.subagent-model-probe/capability-matrix.json")
)


def main():
    parser = argparse.ArgumentParser(
        description="Check subagent capability matrix before fan-out."
    )
    parser.add_argument("--store", default=DEFAULT_STORE,
                        help="Path to the JSON store")
    parser.add_argument("--max-age-days", type=int, default=90,
                        help="Max freshness window in days (default: 90)")
    parser.add_argument("--models", nargs="+", required=True,
                        help="Model identifiers to check")
    args = parser.parse_args()

    data = _load(args.store)
    today = date.today()
    cutoff = today - timedelta(days=args.max_age_days)

    ok = True
    reasons = []

    for model in args.models:
        entry = data.get(model)
        if not entry:
            print(f"{model} → UNTESTED")
            reasons.append(f"{model} untested")
            ok = False
            continue

        result = entry.get("result", "?")
        last_str = entry.get("last_tested", "0000-00-00")
        try:
            last_date = date.fromisoformat(last_str)
        except ValueError:
            last_date = None

        if last_date and last_date < cutoff:
            days_ago = (today - last_date).days
            print(f"{model} → {result.upper()} STALE (tested {days_ago} days ago)")
            reasons.append(f"{model} stale ({days_ago}d)")
            ok = False
        elif result == "works":
            print(f"{model} → works (tested {last_str})")
        else:
            print(f"{model} → {result.upper()} (tested {last_str})")
            reasons.append(f"{model} {result}")
            ok = False

    if ok:
        print("\nSAFE TO FAN OUT")
        sys.exit(0)
    else:
        print(f"\nPROBE FIRST: {', '.join(reasons)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
