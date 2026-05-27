#!/usr/bin/env python3
"""Fetch external datasets listed in a sources.yaml manifest."""

import argparse
import hashlib
import json
import os
import sys
import urllib.request

try:
    import yaml
except ImportError:
    # Fallback: minimal YAML parser for simple key-value lists
    yaml = None


def parse_sources_yaml(path):
    """Parse sources.yaml, with or without PyYAML."""
    with open(path) as f:
        text = f.read()
    if yaml:
        data = yaml.safe_load(text)
        if isinstance(data, dict) and "sources" in data:
            return data
        return {"sources": data if isinstance(data, list) else []}
    # Minimal parser for simple format: list of dicts under 'sources:'
    sources = []
    current = {}
    in_sources = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "" or stripped.startswith("#"):
            continue
        if stripped == "sources:":
            in_sources = True
            continue
        if not in_sources:
            continue
        if stripped.startswith("- "):
            if current:
                sources.append(current)
            current = {}
            stripped = stripped[2:].strip()
        if ":" in stripped:
            key, _, val = stripped.partition(":")
            current[key.strip()] = val.strip().strip('"').strip("'")
    if current:
        sources.append(current)
    return {"sources": sources}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(sources_yaml, output_dir):
    """Fetch datasets and return manifest of fetched files."""
    config = parse_sources_yaml(sources_yaml)
    sources = config.get("sources", [])
    if not sources:
        print("No sources found in", sources_yaml, file=sys.stderr)
        return []

    os.makedirs(output_dir, exist_ok=True)
    manifest = []

    for src in sources:
        url = src.get("url")
        name = src.get("name") or os.path.basename(url)
        dest = os.path.join(output_dir, name)

        print(f"Fetching {name} from {url}...")
        try:
            urllib.request.urlretrieve(url, dest)
            digest = sha256_file(dest)
            entry = {"name": name, "url": url, "path": dest, "sha256": digest}
            manifest.append(entry)
            print(f"  ✓ {name} ({digest[:12]}...)")
        except Exception as e:
            print(f"  ✗ {name}: {e}", file=sys.stderr)
            manifest.append({"name": name, "url": url, "error": str(e)})

    return manifest


def main():
    parser = argparse.ArgumentParser(description="Fetch external datasets from sources.yaml")
    parser.add_argument("sources", nargs="?", default="data/external/sources.yaml",
                        help="Path to sources.yaml (default: data/external/sources.yaml)")
    parser.add_argument("-o", "--output-dir", default="data/external",
                        help="Output directory for fetched files (default: data/external)")
    parser.add_argument("--json", action="store_true", help="Output manifest as JSON")
    args = parser.parse_args()

    manifest = fetch(args.sources, args.output_dir)

    if args.json:
        print(json.dumps(manifest, indent=2))
    else:
        ok = sum(1 for m in manifest if "error" not in m)
        fail = sum(1 for m in manifest if "error" in m)
        print(f"\nFetched {ok} dataset(s), {fail} failed.")

    sys.exit(1 if any("error" in m for m in manifest) else 0)


if __name__ == "__main__":
    main()
