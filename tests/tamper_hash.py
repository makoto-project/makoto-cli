#!/usr/bin/env python3
"""Tamper attestation hash for testing."""
import json, sys

path = sys.argv[1]
with open(path) as f:
    a = json.load(f)
a['subject'][0]['digest']['sha256'] = 'deadbeef' * 8
with open(path, 'w') as f:
    json.dump(a, f)
print('tampered')
