#!/usr/bin/env python3
"""Transform a data file and produce a Makoto DBOM (v0.1) with extended lineage.

Reads the input data file plus its existing DBOM (if any), applies a CSV
filter, and writes:
  - the transformed data file (e.g. `<name>_filtered.csv`)
  - a new DBOM for the output (`<name>_filtered.dbom.json`) whose `lineage[]`
    chains the input's lineage steps + a new transform step

Thin wrapper around the `makoto` Python SDK
(https://usemakoto.dev/sdk/python/). Target: Makoto L1.
"""

import argparse
import csv
import hashlib
import json
import os
import sys

try:
    from makoto import generate
except ImportError:
    print(
        "Error: the `makoto` Python SDK is not installed.\n"
        "Install with:  pip install -r requirements.txt\n"
        "Or for local dev:  pip install -e ../usemakoto.dev/sdk/python",
        file=sys.stderr,
    )
    sys.exit(2)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def transform_filter_csv(input_path, output_path, column, operator, value):
    """Filter CSV rows where `<column> <operator> <value>`."""
    with open(input_path, newline="") as fin:
        reader = csv.DictReader(fin)
        fieldnames = reader.fieldnames
        rows = list(reader)

    try:
        threshold_num = float(value)
        threshold_is_num = True
    except (ValueError, TypeError):
        threshold_num = None
        threshold_is_num = False

    keep = []
    for row in rows:
        cell = row.get(column, "")
        if threshold_is_num:
            try:
                cell_val = float(cell)
                threshold = threshold_num
            except (ValueError, TypeError):
                cell_val = cell
                threshold = value
        else:
            cell_val = cell
            threshold = value

        if operator == ">" and cell_val > threshold:
            keep.append(row)
        elif operator == ">=" and cell_val >= threshold:
            keep.append(row)
        elif operator == "<" and cell_val < threshold:
            keep.append(row)
        elif operator == "<=" and cell_val <= threshold:
            keep.append(row)
        elif operator == "==" and cell_val == threshold:
            keep.append(row)
        elif operator == "!=" and cell_val != threshold:
            keep.append(row)

    with open(output_path, "w", newline="") as fout:
        writer = csv.DictWriter(fout, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(keep)

    return len(rows), len(keep)


def find_input_dbom(input_path, hint=None):
    """Locate the DBOM associated with the input file, if any."""
    if hint and os.path.isfile(hint):
        return hint
    name = os.path.splitext(os.path.basename(input_path))[0]
    candidates = [
        os.path.join("dboms", f"{name}.dbom.json"),
        os.path.join(os.path.dirname(input_path), f"{name}.dbom.json"),
        f"{name}.dbom.json",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Transform a dataset (CSV filter) and produce a new DBOM whose "
            "lineage chains the input DBOM's lineage."
        )
    )
    parser.add_argument("input", help="Input data file (CSV)")
    parser.add_argument(
        "-o",
        "--output",
        help="Output file path (default: <input>_filtered.<ext>)",
    )
    parser.add_argument(
        "--dbom",
        help="Path to the input's DBOM (used to chain lineage). Auto-discovered if omitted.",
    )
    parser.add_argument(
        "--dboms-dir",
        default="dboms",
        help="Output directory for the new DBOM (default: dboms)",
    )
    parser.add_argument(
        "--signer",
        default=None,
        help="Signer identity (defaults to $MAKOTO_SIGNER or 'github:makoto-cli')",
    )
    parser.add_argument(
        "--column", default="temperature_c", help="Column to filter on (default: temperature_c)"
    )
    parser.add_argument(
        "--operator", default=">", help="Comparison operator (default: >)"
    )
    parser.add_argument(
        "--value", default="22", help="Threshold value (default: 22)"
    )
    parser.add_argument("--json", action="store_true", help="Print result as JSON")
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"Error: {args.input} not found", file=sys.stderr)
        sys.exit(1)

    input_path = os.path.abspath(args.input)
    base, ext = os.path.splitext(input_path)
    output_path = os.path.abspath(args.output) if args.output else f"{base}_filtered{ext}"

    # Locate input DBOM and pull its existing lineage chain forward.
    input_dbom_path = find_input_dbom(args.input, args.dbom)
    prior_lineage = []
    input_hash = sha256_file(input_path)
    if input_dbom_path:
        try:
            with open(input_dbom_path) as f:
                input_dbom = json.load(f)
            prior_lineage = list(input_dbom.get("lineage", []))
            recorded_hash = input_dbom.get("source", {}).get("hash", {}).get("value")
            if recorded_hash and recorded_hash != input_hash:
                print(
                    f"⚠ input DBOM hash {recorded_hash[:12]}... does not match "
                    f"current file hash {input_hash[:12]}...; lineage chain may be stale",
                    file=sys.stderr,
                )
        except Exception as e:
            print(f"⚠ could not read input DBOM {input_dbom_path}: {e}", file=sys.stderr)

    # Apply the transform.
    records_in, records_out = transform_filter_csv(
        input_path, output_path, args.column, args.operator, args.value
    )
    output_hash = sha256_file(output_path)

    # Build the new lineage step (chained onto prior).
    next_step = (max((s.get("step", 0) for s in prior_lineage), default=0)) + 1
    transform_step = {
        "step": next_step,
        "description": (
            f"Filter rows where {args.column} {args.operator} {args.value} "
            f"({records_in} → {records_out} records)"
        ),
        "tool": "makoto-cli/transform_data.py (filter)",
        "input_hash": input_hash,
        "output_hash": output_hash,
    }
    lineage_steps = prior_lineage + [transform_step]

    signer = args.signer or os.environ.get("MAKOTO_SIGNER", "github:makoto-cli")

    dbom = generate(
        file_path=output_path,
        signer=signer,
        format=ext.lstrip(".") or None,
        lineage_steps=lineage_steps,
    )

    out_name = os.path.splitext(os.path.basename(output_path))[0]

    if args.json:
        print(json.dumps({"dbom": dbom, "output": output_path}, indent=2))
        return

    os.makedirs(args.dboms_dir, exist_ok=True)
    dbom_path = os.path.join(args.dboms_dir, f"{out_name}.dbom.json")
    with open(dbom_path, "w") as f:
        json.dump(dbom, f, indent=2)
        f.write("\n")

    print(f"✓ Transformed:  {args.input} → {output_path}")
    print(f"  Records:      {records_in} → {records_out}")
    print(f"  DBOM:         {dbom_path}")
    print(f"  Lineage:      {len(lineage_steps)} step(s) (chained)")


if __name__ == "__main__":
    main()
