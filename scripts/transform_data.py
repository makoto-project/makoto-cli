#!/usr/bin/env python3
"""Transform a data artifact and produce a Makoto transform attestation.

Applies a transformation to a CSV/JSON file, generates a transform attestation
(in-toto Statement v1, makoto.dev/transform/v1) linking to the input's origin
attestation, and updates the DBOM with the new transformation entry.

Target: Makoto L1 (Provenance Exists).
"""

import argparse
import csv
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


def count_csv_records(path):
    with open(path) as f:
        return sum(1 for _ in f) - 1


def transform_filter_csv(input_path, output_path, column, operator, value):
    """Filter CSV rows where column <operator> value."""
    with open(input_path, newline="") as fin:
        reader = csv.DictReader(fin)
        fieldnames = reader.fieldnames
        rows = list(reader)

    filtered = []
    for row in rows:
        cell = row.get(column, "")
        try:
            cell_val = float(cell)
            threshold = float(value)
        except (ValueError, TypeError):
            cell_val = cell
            threshold = value

        if operator == ">" and cell_val > threshold:
            filtered.append(row)
        elif operator == ">=" and cell_val >= threshold:
            filtered.append(row)
        elif operator == "<" and cell_val < threshold:
            filtered.append(row)
        elif operator == "<=" and cell_val <= threshold:
            filtered.append(row)
        elif operator == "==" and cell_val == threshold:
            filtered.append(row)
        elif operator == "!=" and cell_val != threshold:
            filtered.append(row)

    with open(output_path, "w", newline="") as fout:
        writer = csv.DictWriter(fout, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(filtered)

    return len(rows), len(filtered)


def generate_transform_attestation(input_path, output_path, input_attestation_ref,
                                    input_digest, transform_name, transform_params,
                                    records_in, records_out, started, finished):
    """Generate a transform attestation (in-toto Statement v1, makoto.dev/transform/v1)."""
    output_digest = sha256_file(output_path)
    output_name = os.path.splitext(os.path.basename(output_path))[0]
    input_name = os.path.splitext(os.path.basename(input_path))[0]

    attestation = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{
            "name": f"dataset:{output_name}",
            "digest": {
                "sha256": output_digest,
                "recordCount": str(records_out)
            }
        }],
        "predicateType": "https://makoto.dev/transform/v1",
        "predicate": {
            "inputs": [{
                "name": f"dataset:{input_name}",
                "digest": {"sha256": input_digest},
                "attestationRef": input_attestation_ref
            }],
            "transform": {
                "type": "https://makoto.dev/transforms/filter",
                "name": transform_name,
                "version": "0.1.0",
                "parameters": transform_params,
                "codeRef": {
                    "uri": "git+https://github.com/makoto-project/makoto-cli@main#scripts/transform_data.py"
                }
            },
            "executor": {
                "id": "https://github.com/makoto-project/makoto-cli",
                "platform": "local"
            },
            "metadata": {
                "startedOn": started,
                "finishedOn": finished,
                "recordsInput": records_in,
                "recordsOutput": records_out
            }
        }
    }
    return attestation


def update_dbom(dbom_path, transform_name, transform_attestation_ref):
    """Add a transformation entry to an existing DBOM."""
    with open(dbom_path) as f:
        dbom = json.load(f)

    transforms = dbom.get("transformations", [])
    order = max((t["order"] for t in transforms), default=0) + 1
    transforms.append({
        "order": order,
        "name": transform_name,
        "attestationRef": transform_attestation_ref
    })
    dbom["transformations"] = transforms

    with open(dbom_path, "w") as f:
        json.dump(dbom, f, indent=2)
        f.write("\n")

    return dbom


def main():
    parser = argparse.ArgumentParser(
        description="Transform a dataset and produce a Makoto transform attestation")
    parser.add_argument("input", help="Input data file (CSV)")
    parser.add_argument("-o", "--output", help="Output file path (default: <input>_filtered.<ext>)")
    parser.add_argument("--dbom", help="Path to the input's DBOM file (to update with transform)")
    parser.add_argument("--attestation-ref",
                        help="Path to the input's origin attestation (for lineage chain)")
    parser.add_argument("--attestations-dir", default="attestations",
                        help="Output directory for transform attestation")
    parser.add_argument("--column", default="temperature_c",
                        help="Column to filter on (default: temperature_c)")
    parser.add_argument("--operator", default=">",
                        help="Comparison operator (default: >)")
    parser.add_argument("--value", default="22",
                        help="Threshold value (default: 22)")
    parser.add_argument("--json", action="store_true", help="Print output as JSON")
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"Error: {args.input} not found", file=sys.stderr)
        sys.exit(1)

    # Determine output path
    base, ext = os.path.splitext(args.input)
    output_path = args.output or f"{base}_filtered{ext}"
    input_name = os.path.splitext(os.path.basename(args.input))[0]
    output_name = os.path.splitext(os.path.basename(output_path))[0]

    # Resolve input attestation ref
    attestation_ref = args.attestation_ref
    if not attestation_ref:
        # Try to find it from the DBOM
        if args.dbom and os.path.isfile(args.dbom):
            with open(args.dbom) as f:
                dbom = json.load(f)
            sources = dbom.get("sources", [])
            if sources:
                attestation_ref = sources[0].get("attestationRef")

    input_digest = sha256_file(args.input)
    started = datetime.now(timezone.utc).isoformat()

    # Apply transformation
    transform_name = f"Filter {args.column} {args.operator} {args.value}"
    transform_params = {
        "column": args.column,
        "operator": args.operator,
        "value": args.value
    }

    records_in, records_out = transform_filter_csv(
        args.input, output_path, args.column, args.operator, args.value
    )

    finished = datetime.now(timezone.utc).isoformat()

    # Generate transform attestation
    tx_attestation = generate_transform_attestation(
        args.input, output_path, attestation_ref or "",
        input_digest, transform_name, transform_params,
        records_in, records_out, started, finished
    )

    tx_filename = f"{output_name}.transform.json"
    tx_ref = os.path.join(args.attestations_dir, tx_filename)

    if args.json:
        print(json.dumps({"attestation": tx_attestation, "output": output_path}, indent=2))
    else:
        os.makedirs(args.attestations_dir, exist_ok=True)
        tx_path = os.path.join(args.attestations_dir, tx_filename)

        with open(tx_path, "w") as f:
            json.dump(tx_attestation, f, indent=2)
            f.write("\n")
        print(f"✓ Transformed:  {args.input} → {output_path}")
        print(f"  Records:      {records_in} → {records_out}")
        print(f"  Attestation:  {tx_path}")

        # Update DBOM if provided
        if args.dbom and os.path.isfile(args.dbom):
            update_dbom(args.dbom, transform_name, tx_ref)
            print(f"  DBOM updated: {args.dbom}")


if __name__ == "__main__":
    main()
