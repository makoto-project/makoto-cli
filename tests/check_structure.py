#!/usr/bin/env python3
"""Verify in-toto attestation + DBOM structure."""
import json, sys

att_path, dbom_path = sys.argv[1], sys.argv[2]
with open(att_path) as f:
    a = json.load(f)
with open(dbom_path) as f:
    d = json.load(f)

ok = (a['_type'] == 'https://in-toto.io/Statement/v1'
      and a['predicateType'] == 'https://makoto.dev/origin/v1'
      and 'sha256' in a['subject'][0]['digest']
      and d['dbomVersion'] == '1.0.0'
      and d['dataset']['makotoLevel'] == 'L1')
print('ok' if ok else 'fail')
sys.exit(0 if ok else 1)
