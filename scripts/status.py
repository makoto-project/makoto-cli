#!/usr/bin/env python3
"""Show a summary table of all data assets and their DBOM status (v0.1)."""

import json
import os
import sys


def main():
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data"
    dboms_dir = sys.argv[2] if len(sys.argv) > 2 else "dboms"

    assets = []
    for dirpath, _, filenames in os.walk(data_dir):
        for f in sorted(filenames):
            if f.endswith((".csv", ".json", ".parquet")) and f != "sources.yaml":
                assets.append(os.path.join(dirpath, f))

    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║                       DBOM Status Summary                            ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(
        f"║ {'Asset':<28} │ {'DBOM':<6} │ {'Schema':<8} │ {'Signer':<18} ║"
    )
    print("╠══════════════════════════════════════════════════════════════════════╣")

    for f in assets:
        name = os.path.splitext(os.path.basename(f))[0]
        dbom_file = os.path.join(dboms_dir, f"{name}.dbom.json")
        if os.path.isfile(dbom_file):
            try:
                with open(dbom_file) as df:
                    dbom = json.load(df)
                schema = "v" + dbom.get("schema_version", "?")
                signer = dbom.get("signature", {}).get("signer", "?")
            except Exception:
                schema = "?"
                signer = "?"
            print(
                f"║ {name[:28]:<28} │ {'✓':<6} │ {schema:<8} │ {signer[:18]:<18} ║"
            )
        else:
            print(
                f"║ {name[:28]:<28} │ {'✗':<6} │ {'—':<8} │ {'—':<18} ║"
            )

    print("╚══════════════════════════════════════════════════════════════════════╝")


if __name__ == "__main__":
    main()
