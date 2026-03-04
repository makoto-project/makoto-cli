#!/usr/bin/env python3
"""Validate DBOM documents and their referenced attestations.

Implements the Makoto 4-step verification process:
  1. Fetch attestation — locate attestation referenced by DBOM
  2. Verify signature — at L1, verify structure/format; at L2+, verify DSSE
  3. Check data hash — compute SHA-256, compare to attestation subject digest
  4. Verify lineage — recursively verify input attestations in transforms

Target: Makoto L1 (Provenance Exists).
"""

import argparse
import hashlib
import json
import os
import sys

VALID_PREDICATE_TYPES = {
    "https://makoto.dev/origin/v1",
    "https://makoto.dev/transform/v1",
    "https://makoto.dev/stream-window/v1",
}

INTOTO_STATEMENT_V1 = "https://in-toto.io/Statement/v1"


class ValidationResult:
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
        print(f"\n{'✓' if self.passed else '✗'} {self.target}: {status}")
        for s in self.steps:
            icon = "  ✓" if s["passed"] else "  ✗"
            detail = f" — {s['detail']}" if s["detail"] else ""
            print(f"{icon} {s['step']}{detail}")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path):
    with open(path) as f:
        return json.load(f)


def resolve_path(ref, base_dir):
    """Resolve an attestation ref relative to a base directory."""
    if os.path.isabs(ref):
        return ref
    return os.path.join(base_dir, ref)


def validate_attestation_structure(attestation):
    """Validate in-toto Statement v1 structure."""
    errors = []
    if attestation.get("_type") != INTOTO_STATEMENT_V1:
        errors.append(f"_type must be {INTOTO_STATEMENT_V1}")
    subjects = attestation.get("subject", [])
    if not subjects:
        errors.append("subject array is empty")
    for i, s in enumerate(subjects):
        if "name" not in s:
            errors.append(f"subject[{i}] missing name")
        digest = s.get("digest", {})
        if "sha256" not in digest:
            errors.append(f"subject[{i}] missing digest.sha256")
    pred_type = attestation.get("predicateType", "")
    if pred_type not in VALID_PREDICATE_TYPES:
        errors.append(f"predicateType '{pred_type}' not recognized")
    if "predicate" not in attestation:
        errors.append("predicate is missing")
    return errors


def validate_data_hash(attestation, data_path, base_dir):
    """Check SHA-256 of data artifact against attestation subject digest."""
    if not data_path:
        return False, "no data path provided"
    resolved = resolve_path(data_path, base_dir)
    if not os.path.isfile(resolved):
        return False, f"data file not found: {resolved}"
    actual = sha256_file(resolved)
    expected = attestation["subject"][0]["digest"]["sha256"]
    if actual == expected:
        return True, f"sha256 match ({actual[:16]}...)"
    return False, f"sha256 mismatch: expected {expected[:16]}..., got {actual[:16]}..."


def infer_data_path(attestation):
    """Try to infer the data file path from the attestation origin source."""
    predicate = attestation.get("predicate", {})
    origin = predicate.get("origin", {})
    source = origin.get("source", "")
    if source.startswith("file://"):
        return source[7:]
    return None


def validate_lineage(attestation, base_dir, visited=None):
    """Recursively verify input attestations referenced in transform predicates."""
    if visited is None:
        visited = set()

    predicate = attestation.get("predicate", {})
    inputs = predicate.get("inputs", [])
    if not inputs:
        return True, "no inputs (origin attestation)"

    results = []
    for inp in inputs:
        ref = inp.get("attestationRef")
        if not ref:
            results.append((True, f"input '{inp.get('name', '?')}' has no attestationRef (L1 acceptable)"))
            continue
        if ref in visited:
            results.append((True, f"input '{inp.get('name', '?')}' already verified"))
            continue
        visited.add(ref)

        ref_path = resolve_path(ref, base_dir)
        if not os.path.isfile(ref_path):
            results.append((False, f"input attestation not found: {ref_path}"))
            continue

        input_att = load_json(ref_path)
        errors = validate_attestation_structure(input_att)
        if errors:
            results.append((False, f"input attestation invalid: {'; '.join(errors)}"))
            continue

        # Check hash of input matches
        expected_hash = inp.get("digest", {}).get("sha256")
        actual_hash = input_att.get("subject", [{}])[0].get("digest", {}).get("sha256")
        if expected_hash and actual_hash and expected_hash != actual_hash:
            results.append((False, f"input hash mismatch for '{inp.get('name', '?')}'"))
            continue

        # Recurse
        ok, detail = validate_lineage(input_att, base_dir, visited)
        results.append((ok, f"input '{inp.get('name', '?')}': {detail}"))

    all_ok = all(r[0] for r in results)
    detail = "; ".join(r[1] for r in results)
    return all_ok, detail


def validate_dbom(dbom_path, data_dir=None):
    """Validate a DBOM and all its referenced attestations."""
    base_dir = os.path.dirname(os.path.abspath(dbom_path))
    # If dbom is in dboms/, look for attestations relative to parent
    if os.path.basename(base_dir) == "dboms":
        base_dir = os.path.dirname(base_dir)

    result = ValidationResult(dbom_path)
    dbom = load_json(dbom_path)

    # Step 0: DBOM structure
    required = ["dbomVersion", "dataset", "sources"]
    missing = [k for k in required if k not in dbom]
    result.step("DBOM structure", not missing,
                f"missing fields: {missing}" if missing else "valid")
    if missing:
        return result

    dataset = dbom.get("dataset", {})
    level = dataset.get("makotoLevel", "?")
    result.step("Makoto level", level in ("L1", "L2", "L3"), f"level: {level}")

    # Validate each source attestation
    for src in dbom.get("sources", []):
        ref = src.get("attestationRef")
        if not ref:
            result.step(f"Source '{src.get('name', '?')}' attestation", False, "missing attestationRef")
            continue

        ref_path = resolve_path(ref, base_dir)

        # Step 1: Fetch attestation
        if not os.path.isfile(ref_path):
            result.step(f"1. Fetch [{src['name']}]", False, f"not found: {ref_path}")
            continue
        attestation = load_json(ref_path)
        result.step(f"1. Fetch [{src['name']}]", True, ref_path)

        # Step 2: Verify structure (L1) / signature (L2+)
        errors = validate_attestation_structure(attestation)
        result.step(f"2. Structure [{src['name']}]", not errors,
                    "; ".join(errors) if errors else "in-toto Statement v1 valid")

        # Step 3: Check data hash
        data_path = infer_data_path(attestation)
        if data_dir and data_path:
            # Try relative to data_dir first
            pass
        if data_path:
            ok, detail = validate_data_hash(attestation, data_path, base_dir)
            result.step(f"3. Data hash [{src['name']}]", ok, detail)
        else:
            result.step(f"3. Data hash [{src['name']}]", True, "skipped (no data path)")

        # Step 4: Verify lineage
        ok, detail = validate_lineage(attestation, base_dir)
        result.step(f"4. Lineage [{src['name']}]", ok, detail)

    # Validate transform attestations
    for tx in dbom.get("transformations", []):
        ref = tx.get("attestationRef")
        if not ref:
            continue
        ref_path = resolve_path(ref, base_dir)
        if not os.path.isfile(ref_path):
            result.step(f"Transform [{tx.get('name', '?')}]", False, f"not found: {ref_path}")
            continue
        tx_att = load_json(ref_path)
        errors = validate_attestation_structure(tx_att)
        result.step(f"Transform [{tx.get('name', '?')}] structure", not errors,
                    "; ".join(errors) if errors else "valid")
        ok, detail = validate_lineage(tx_att, base_dir)
        result.step(f"Transform [{tx.get('name', '?')}] lineage", ok, detail)

    return result


def main():
    parser = argparse.ArgumentParser(description="Validate a DBOM and its attestations")
    parser.add_argument("dbom", nargs="?", help="Path to a DBOM JSON file")
    parser.add_argument("--all", action="store_true",
                        help="Validate all DBOMs in the dboms/ directory")
    parser.add_argument("--dboms-dir", default="dboms",
                        help="Directory containing DBOMs (default: dboms)")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    if not args.dbom and not args.all:
        parser.error("Provide a DBOM path or use --all")

    results = []

    if args.all:
        dboms_dir = args.dboms_dir
        if not os.path.isdir(dboms_dir):
            print(f"Error: {dboms_dir} not found", file=sys.stderr)
            sys.exit(1)
        for f in sorted(os.listdir(dboms_dir)):
            if f.endswith(".dbom.json"):
                results.append(validate_dbom(os.path.join(dboms_dir, f)))
    else:
        results.append(validate_dbom(args.dbom))

    if args.json:
        print(json.dumps([r.to_dict() for r in results], indent=2))
    else:
        for r in results:
            r.print_report()

    all_passed = all(r.passed for r in results)
    if not args.json:
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        print(f"\n{'═' * 40}")
        print(f"{'✓' if all_passed else '✗'} {passed}/{total} DBOM(s) passed validation")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
