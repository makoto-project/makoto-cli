#!/usr/bin/env python3
"""Verify the transformed-output DBOM has a chained lineage (≥ 2 steps).

Usage: check_transform.py <transformed-dbom-path>
"""
import json
import sys

dbom_path = sys.argv[1]
with open(dbom_path) as f:
    d = json.load(f)

lineage = d.get("lineage", [])
if len(lineage) < 2:
    print(
        f"fail: transformed DBOM must have ≥ 2 lineage steps, got {len(lineage)}"
    )
    sys.exit(1)

# The latest step should describe a transformation and chain hashes.
last = lineage[-1]
prev = lineage[-2]
ok = True
if last.get("input_hash") in (None, "n/a", ""):
    ok = False
    print("fail: last lineage step has no input_hash")
if last.get("input_hash") != prev.get("output_hash"):
    ok = False
    print(
        "fail: last lineage step input_hash does not chain to previous output_hash"
    )
if not last.get("description"):
    ok = False
    print("fail: last lineage step has no description")

if ok:
    print("ok")
    sys.exit(0)
sys.exit(1)
