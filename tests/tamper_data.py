#!/usr/bin/env python3
"""Tamper the data file referenced by a DBOM by appending an extra row.

This invalidates the recorded `source.hash.value` so `verify()` will flag
a hash mismatch. Used by the tamper-detection test.

Usage:
    tamper_data.py <data-file>
"""
import sys

path = sys.argv[1]
with open(path, "ab") as f:
    f.write(b"\n999,TAMPERED,9999\n")
print("tampered")
