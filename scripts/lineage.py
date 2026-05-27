#!/usr/bin/env python3
"""Show the DBOM lineage chain for an asset."""

import json
import os
import sys


def show(dbom_path):
    if not os.path.isfile(dbom_path):
        print(f"Error: {dbom_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(dbom_path) as f:
        dbom = json.load(f)

    source = dbom.get("source", {})
    sig = dbom.get("signature", {})
    lineage = dbom.get("lineage", [])

    print(f"Lineage for: {dbom_path}")
    print("─" * 60)
    print(f"  schema_version:  {dbom.get('schema_version', '?')}")
    print(f"  id:              {dbom.get('id', '?')}")
    print(f"  created_at:      {dbom.get('created_at', '?')}")
    print(f"  source.uri:      {source.get('uri', '?')}")
    print(f"  source.format:   {source.get('format', '?')}")
    print(f"  source.hash:     {source.get('hash', {}).get('value', '?')[:16]}...")
    print(f"  signature.signer:{sig.get('signer', '?')}")
    print()
    print(f"  Lineage ({len(lineage)} step(s)):")
    for entry in lineage:
        step = entry.get("step", "?")
        desc = entry.get("description", "?")
        tool = entry.get("tool", "?")
        in_hash = entry.get("input_hash", "?")
        out_hash = entry.get("output_hash", "?")
        in_disp = in_hash if in_hash == "n/a" else f"{in_hash[:12]}..."
        out_disp = f"{out_hash[:12]}..." if out_hash and out_hash != "n/a" else out_hash
        print(f"    [{step}] {desc}")
        print(f"        tool:    {tool}")
        print(f"        input:   {in_disp}")
        print(f"        output:  {out_disp}")


def main():
    if len(sys.argv) < 2:
        print("Usage: lineage.py <dbom-file>", file=sys.stderr)
        sys.exit(1)
    show(sys.argv[1])


if __name__ == "__main__":
    main()
