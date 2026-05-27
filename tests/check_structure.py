#!/usr/bin/env python3
"""Verify a Makoto v0.1 DBOM structure."""
import json
import re
import sys

dbom_path = sys.argv[1]
with open(dbom_path) as f:
    d = json.load(f)

required_top = ["schema_version", "id", "created_at", "source", "signature", "lineage"]
ok = True
errors = []
for k in required_top:
    if k not in d:
        ok = False
        errors.append(f"missing top-level field: {k}")

if d.get("schema_version") != "0.1":
    ok = False
    errors.append(f"schema_version must be '0.1', got {d.get('schema_version')!r}")

if not isinstance(d.get("id", ""), str) or not d.get("id", "").startswith("dbom-"):
    ok = False
    errors.append("id must start with 'dbom-'")

src = d.get("source", {})
for k in ("uri", "hash", "format"):
    if k not in src:
        ok = False
        errors.append(f"missing source.{k}")
h = src.get("hash", {})
if h.get("algorithm") != "sha256":
    ok = False
    errors.append("source.hash.algorithm must be sha256")
val = h.get("value", "")
if not re.fullmatch(r"[a-f0-9]{64}", val):
    ok = False
    errors.append("source.hash.value must be a 64-char hex sha256")

sig = d.get("signature", {})
for k in ("algorithm", "value", "signer"):
    if k not in sig:
        ok = False
        errors.append(f"missing signature.{k}")

lineage = d.get("lineage", [])
if not isinstance(lineage, list) or len(lineage) < 1:
    ok = False
    errors.append("lineage must be a non-empty list")
else:
    for i, step in enumerate(lineage):
        for k in ("step", "description", "tool", "input_hash", "output_hash"):
            if k not in step:
                ok = False
                errors.append(f"lineage[{i}] missing {k}")

if ok:
    print("ok")
    sys.exit(0)
else:
    for e in errors:
        print(f"fail: {e}")
    sys.exit(1)
