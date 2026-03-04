#!/usr/bin/env python3
"""Verify transform attestation structure."""
import json, sys

with open(sys.argv[1]) as f:
    a = json.load(f)

ok = (a['_type'] == 'https://in-toto.io/Statement/v1'
      and a['predicateType'] == 'https://makoto.dev/transform/v1'
      and len(a['predicate']['inputs']) > 0)
print('ok' if ok else 'fail')
sys.exit(0 if ok else 1)
