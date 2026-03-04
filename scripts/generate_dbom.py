#!/usr/bin/env python3
"""Generate origin attestations and DBOM documents for data artifacts.

Produces:
  - An origin attestation (in-toto Statement v1, makoto.dev/origin/v1)
  - A DBOM document referencing the attestation

Target: Makoto L1 (Provenance Exists) — unsigned JSON attestations.
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def count_records(path):
    """Count records in a CSV (lines minus header) or JSON array."""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".csv":
            with open(path) as f:
                return str(sum(1 for _ in f) - 1)
        elif ext == ".json":
            with open(path) as f:
                data = json.load(f)
            if isinstance(data, list):
                return str(len(data))
    except Exception:
        pass
    return None


def generate_origin_attestation(file_path, source_type="file", geography=None,
                                 collector_id=None, collector_version=None):
    """Generate an origin attestation for a data artifact."""
    digest = sha256_file(file_path)
    record_count = count_records(file_path)
    ext = os.path.splitext(file_path)[1].lstrip(".")
    name = os.path.splitext(os.path.basename(file_path))[0]
    now = datetime.now(timezone.utc).isoformat()

    subject_digest = {"sha256": digest}
    if record_count:
        subject_digest["recordCount"] = record_count

    attestation = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{
            "name": f"dataset:{name}",
            "digest": subject_digest
        }],
        "predicateType": "https://makoto.dev/origin/v1",
        "predicate": {
            "origin": {
                "source": f"file://{file_path}",
                "sourceType": source_type,
                "collectionMethod": "manual-upload",
                "collectionTimestamp": now,
            },
            "collector": {
                "id": collector_id or "https://github.com/makoto-project/dbom",
                "version": {"dbom-cli": collector_version or "0.1.0"}
            },
            "schema": {
                "format": ext or "unknown"
            }
        }
    }

    if geography:
        attestation["predicate"]["origin"]["geography"] = geography

    return attestation


def generate_dbom(name, attestation_ref, geography=None, version="1.0.0"):
    """Generate a DBOM document referencing an origin attestation."""
    now = datetime.now(timezone.utc).isoformat()
    dbom = {
        "dbomVersion": "1.0.0",
        "dataset": {
            "name": name,
            "version": version,
            "created": now,
            "makotoLevel": "L1"
        },
        "sources": [{
            "name": name,
            "attestationRef": attestation_ref,
            "makotoLevel": "L1"
        }],
        "transformations": []
    }
    if geography:
        dbom["sources"][0]["geography"] = geography
    return dbom


def main():
    parser = argparse.ArgumentParser(
        description="Generate an origin attestation and DBOM for a data artifact")
    parser.add_argument("file", help="Path to the data file")
    parser.add_argument("--attestations-dir", default="attestations",
                        help="Output directory for attestations (default: attestations)")
    parser.add_argument("--dboms-dir", default="dboms",
                        help="Output directory for DBOMs (default: dboms)")
    parser.add_argument("--source-type", default="file",
                        help="Source type (default: file)")
    parser.add_argument("--geography", default=None,
                        help="Geographic region (e.g., US-WEST-2)")
    parser.add_argument("--version", default="1.0.0",
                        help="Dataset version (default: 1.0.0)")
    parser.add_argument("--collector-id", default=None,
                        help="Collector identifier URI")
    parser.add_argument("--json", action="store_true",
                        help="Print outputs as JSON to stdout instead of writing files")
    args = parser.parse_args()

    if not os.path.isfile(args.file):
        print(f"Error: {args.file} not found", file=sys.stderr)
        sys.exit(1)

    name = os.path.splitext(os.path.basename(args.file))[0]

    # Generate origin attestation
    attestation = generate_origin_attestation(
        args.file,
        source_type=args.source_type,
        geography=args.geography,
        collector_id=args.collector_id,
    )

    attestation_filename = f"{name}.origin.json"
    attestation_ref = os.path.join(args.attestations_dir, attestation_filename)

    # Generate DBOM
    dbom = generate_dbom(name, attestation_ref, geography=args.geography, version=args.version)

    if args.json:
        print(json.dumps({"attestation": attestation, "dbom": dbom}, indent=2))
    else:
        os.makedirs(args.attestations_dir, exist_ok=True)
        os.makedirs(args.dboms_dir, exist_ok=True)

        attestation_path = os.path.join(args.attestations_dir, attestation_filename)
        dbom_path = os.path.join(args.dboms_dir, f"{name}.dbom.json")

        with open(attestation_path, "w") as f:
            json.dump(attestation, f, indent=2)
            f.write("\n")
        print(f"✓ Attestation: {attestation_path}")

        with open(dbom_path, "w") as f:
            json.dump(dbom, f, indent=2)
            f.write("\n")
        print(f"✓ DBOM:        {dbom_path}")

        print(f"  Subject:     {attestation['subject'][0]['name']}")
        print(f"  SHA-256:     {attestation['subject'][0]['digest']['sha256'][:16]}...")
        print(f"  Level:       L1 (Provenance Exists)")


if __name__ == "__main__":
    main()
