#!/usr/bin/env python3
"""Generate a Makoto DBOM (v0.1) for a data file.

Thin wrapper around the `makoto` Python SDK
(https://usemakoto.dev/sdk/python/). Produces one self-contained
`<name>.dbom.json` file conforming to https://usemakoto.dev/schema/v0.1.json.

Target: Makoto L1 (Provenance Exists).
"""

import argparse
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


def main():
    parser = argparse.ArgumentParser(
        description="Generate a Makoto DBOM (v0.1) for a data file."
    )
    parser.add_argument("file", help="Path to the data file")
    parser.add_argument(
        "--dboms-dir",
        default="dboms",
        help="Output directory for the DBOM (default: dboms)",
    )
    parser.add_argument(
        "--signer",
        default=None,
        help=(
            "Signer identity (e.g. github:username). "
            "Defaults to $MAKOTO_SIGNER or 'github:makoto-cli'."
        ),
    )
    parser.add_argument(
        "--uri",
        default=None,
        help="Source URI (defaults to file:// path)",
    )
    parser.add_argument(
        "--format",
        default=None,
        help="Data format (inferred from extension if omitted)",
    )
    parser.add_argument(
        "--collector-id",
        default=None,
        help=(
            "Collector identifier URI (recorded as the lineage tool). "
            "Useful for tracking which CI workflow generated the DBOM."
        ),
    )
    parser.add_argument(
        "--version",
        default=None,
        help="Dataset version (recorded in the lineage step description).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the DBOM as JSON to stdout instead of writing the file",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.file):
        print(f"Error: {args.file} not found", file=sys.stderr)
        sys.exit(1)

    # The SDK calls Path.as_uri() when uri is None, which requires an
    # absolute path. Resolve before passing in.
    file_path = os.path.abspath(args.file)

    signer = args.signer or os.environ.get("MAKOTO_SIGNER", "github:makoto-cli")

    description = "Direct ingestion"
    if args.version:
        description += f" (dataset version {args.version})"
    tool = args.collector_id or "makoto-cli (https://github.com/makoto-project/makoto-cli)"

    lineage_steps = None
    if args.collector_id or args.version:
        import hashlib

        sha = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha.update(chunk)
        file_hash = sha.hexdigest()
        lineage_steps = [
            {
                "step": 1,
                "description": description,
                "tool": tool,
                "input_hash": "n/a",
                "output_hash": file_hash,
            }
        ]

    dbom = generate(
        file_path=file_path,
        signer=signer,
        uri=args.uri,
        format=args.format,
        lineage_steps=lineage_steps,
    )

    name = os.path.splitext(os.path.basename(args.file))[0]

    if args.json:
        print(json.dumps(dbom, indent=2))
        return

    os.makedirs(args.dboms_dir, exist_ok=True)
    dbom_path = os.path.join(args.dboms_dir, f"{name}.dbom.json")
    with open(dbom_path, "w") as f:
        json.dump(dbom, f, indent=2)
        f.write("\n")

    sha256 = dbom["source"]["hash"]["value"]
    print(f"✓ DBOM:     {dbom_path}")
    print(f"  Source:   {dbom['source']['uri']}")
    print(f"  SHA-256:  {sha256[:16]}...")
    print(f"  Signer:   {dbom['signature']['signer']}")
    print(f"  Schema:   v{dbom['schema_version']}  (Makoto L1)")


if __name__ == "__main__":
    main()
