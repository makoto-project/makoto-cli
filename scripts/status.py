#!/usr/bin/env python3
"""Show DBOM status summary table for all data assets."""

import json
import os
import sys


def main():
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data"
    dboms_dir = sys.argv[2] if len(sys.argv) > 2 else "dboms"

    # Find all data assets
    assets = []
    for dirpath, _, filenames in os.walk(data_dir):
        for f in sorted(filenames):
            if f.endswith((".csv", ".json", ".parquet")) and f != "sources.yaml":
                assets.append(os.path.join(dirpath, f))

    print("╔══════════════════════════════════════════════════════════╗")
    print("║                   DBOM Status Summary                    ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║ {'Asset':<30} │ {'DBOM':<8} │ {'Level':<12} ║")
    print("╠══════════════════════════════════════════════════════════╣")

    for f in assets:
        name = os.path.splitext(os.path.basename(f))[0]
        dbom_file = os.path.join(dboms_dir, f"{name}.dbom.json")
        if os.path.isfile(dbom_file):
            try:
                with open(dbom_file) as df:
                    dbom = json.load(df)
                level = dbom.get("dataset", {}).get("makotoLevel", "?")
            except Exception:
                level = "?"
            print(f"║ {name:<30} │ {'✓':<8} │ {level:<12} ║")
        else:
            print(f"║ {name:<30} │ {'✗':<8} │ {'—':<12} ║")

    print("╚══════════════════════════════════════════════════════════╝")


if __name__ == "__main__":
    main()
