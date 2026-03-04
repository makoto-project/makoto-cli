#!/usr/bin/env python3
"""Show DBOM lineage chain for an asset."""

import json
import os
import sys


def show(path, depth=0, visited=None):
    if visited is None:
        visited = set()
    if path in visited:
        return
    visited.add(path)
    if not os.path.isfile(path):
        print("  " * depth + "✗ " + path + " (not found)")
        return
    att = json.load(open(path))
    pred_type = att.get("predicateType", "")
    parts = pred_type.split("/")
    ptype = parts[-2] if len(parts) >= 2 else "?"
    name = att.get("subject", [{}])[0].get("name", "?")
    digest = att.get("subject", [{}])[0].get("digest", {}).get("sha256", "?")[:12]
    print("  " * depth + f"-> {ptype}: {name} ({digest}...)")
    for inp in att.get("predicate", {}).get("inputs", []):
        ref = inp.get("attestationRef", "")
        if ref:
            base = os.path.dirname(os.path.abspath(path))
            if os.path.basename(base) == "attestations":
                base = os.path.dirname(base)
            show(os.path.join(base, ref), depth + 1, visited)


def main():
    if len(sys.argv) < 2:
        print("Usage: lineage.py <dbom-file>", file=sys.stderr)
        sys.exit(1)

    dbom_path = sys.argv[1]
    if not os.path.isfile(dbom_path):
        print(f"Error: {dbom_path} not found", file=sys.stderr)
        sys.exit(1)

    print(f"Lineage for: {dbom_path}")
    print("─" * 40)

    dbom = json.load(open(dbom_path))
    base_dir = os.path.dirname(os.path.abspath(dbom_path))
    if os.path.basename(base_dir) == "dboms":
        base_dir = os.path.dirname(base_dir)

    for src in dbom.get("sources", []):
        ref = src.get("attestationRef", "")
        if ref:
            show(os.path.join(base_dir, ref))
    for tx in dbom.get("transformations", []):
        ref = tx.get("attestationRef", "")
        if ref:
            show(os.path.join(base_dir, ref))


if __name__ == "__main__":
    main()
