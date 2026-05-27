#!/usr/bin/env python3
"""Validate Makoto DBOMs (v0.1) and their referenced data files.

Thin wrapper around `makoto.verify()` from the Makoto Python SDK
(https://usemakoto.dev/sdk/python/).

Validation steps performed by the SDK:

  1. Schema validation against https://usemakoto.dev/schema/v0.1.json
  2. SHA-256 hash of the data file matches `source.hash.value`
     (only when a data file is provided / inferable)

Target: Makoto L1 (Provenance Exists).
"""

import argparse
import json
import os
import sys

try:
    from makoto import verify
except ImportError:
    print(
        "Error: the `makoto` Python SDK is not installed.\n"
        "Install with:  pip install -r requirements.txt\n"
        "Or for local dev:  pip install -e ../usemakoto.dev/sdk/python",
        file=sys.stderr,
    )
    sys.exit(2)


class ValidationResult:
    """Carry per-DBOM validation results in a shape friendly to humans + JSON."""

    def __init__(self, target):
        self.target = target
        self.steps = []
        self.passed = True

    def step(self, name, ok, detail=""):
        self.steps.append({"step": name, "passed": ok, "detail": detail})
        if not ok:
            self.passed = False

    def to_dict(self):
        return {"target": self.target, "passed": self.passed, "steps": self.steps}

    def print_report(self):
        status = "PASS" if self.passed else "FAIL"
        icon = "✓" if self.passed else "✗"
        print(f"\n{icon} {self.target}: {status}")
        for s in self.steps:
            mark = "  ✓" if s["passed"] else "  ✗"
            detail = f" — {s['detail']}" if s["detail"] else ""
            print(f"{mark} {s['step']}{detail}")


def _infer_data_path(dbom, dbom_path):
    """Find the data file referenced by the DBOM.

    Tries, in order:
      1. The `source.uri` if it points to an existing file:// path.
      2. <name>.<format> in the directory two levels up (`data/local/`,
         `data/external/`) or in the working directory — covers the common
         layout produced by `just generate`.
    """
    src = dbom.get("source", {})
    uri = src.get("uri", "")
    if uri.startswith("file://"):
        path = uri[7:]
        if os.path.isfile(path):
            return path

    name = os.path.splitext(os.path.basename(dbom_path))[0]
    if name.endswith(".dbom"):
        name = name[:-5]
    ext = src.get("format", "")
    fname = f"{name}.{ext}" if ext else name

    # Walk up looking for a data/ tree.
    cur = os.path.dirname(os.path.abspath(dbom_path))
    for _ in range(4):
        for sub in ("data/local", "data/external", "data", "."):
            candidate = os.path.join(cur, sub, fname)
            if os.path.isfile(candidate):
                return candidate
        cur = os.path.dirname(cur)
    return None


def validate_one(dbom_path):
    result = ValidationResult(dbom_path)

    try:
        with open(dbom_path) as f:
            dbom = json.load(f)
    except Exception as e:
        result.step("Read DBOM", False, str(e))
        return result
    result.step("Read DBOM", True, f"loaded {dbom_path}")

    data_path = _infer_data_path(dbom, dbom_path)
    verify_result = verify(dbom, file_path=data_path)

    if data_path:
        result.step("Locate data file", True, data_path)
    else:
        result.step(
            "Locate data file", True, "skipped (file not found; schema-only)"
        )

    hash_error_seen = False
    schema_errors = []
    for err in verify_result.errors:
        if err.startswith("File hash mismatch"):
            hash_error_seen = True
            result.step("Data hash", False, err)
        else:
            schema_errors.append(err)

    if schema_errors:
        result.step("Schema (v0.1)", False, "; ".join(schema_errors))
    else:
        result.step("Schema (v0.1)", True, "valid")

    if data_path and not hash_error_seen:
        result.step("Data hash", True, "sha256 match")

    sig = dbom.get("signature", {})
    if sig.get("signer"):
        result.step("Signature", True, f"signer={sig['signer']} (L1: unsigned)")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Validate a Makoto DBOM (v0.1) against schema + data hash"
    )
    parser.add_argument("dbom", nargs="?", help="Path to a DBOM JSON file")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Validate all DBOMs in the dboms/ directory",
    )
    parser.add_argument(
        "--dboms-dir",
        default="dboms",
        help="Directory containing DBOMs (default: dboms)",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if not args.dbom and not args.all:
        parser.error("Provide a DBOM path or use --all")

    results = []
    if args.all:
        if not os.path.isdir(args.dboms_dir):
            print(f"Error: {args.dboms_dir} not found", file=sys.stderr)
            sys.exit(1)
        for f in sorted(os.listdir(args.dboms_dir)):
            if f.endswith(".dbom.json"):
                results.append(validate_one(os.path.join(args.dboms_dir, f)))
    else:
        results.append(validate_one(args.dbom))

    if args.json:
        print(json.dumps([r.to_dict() for r in results], indent=2))
    else:
        for r in results:
            r.print_report()
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        all_ok = passed == total
        icon = "✓" if all_ok else "✗"
        print(f"\n{'═' * 40}")
        print(f"{icon} {passed}/{total} DBOM(s) passed validation")

    sys.exit(0 if all(r.passed for r in results) else 1)


if __name__ == "__main__":
    main()
