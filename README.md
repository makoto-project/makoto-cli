# makoto-cli

A CLI toolkit for generating, validating, and managing [Makoto](https://usemakoto.dev) **Data Bills of Materials (DBOMs)** — signed attestations that prove where your data came from and how it was transformed.

Built as a [Justfile](https://github.com/casey/just) following the [makoto-project/justfiles](https://github.com/makoto-project/justfiles) pattern: clone it, alias it, use it from anywhere.

## Install

```bash
# Prerequisites: just, python3
# macOS
brew install just

# Clone and alias
git clone https://github.com/makoto-project/makoto-cli.git ~/makoto-cli
echo "alias makoto-cli='just --justfile ~/makoto-cli/Justfile'" >> ~/.bashrc
source ~/.bashrc
```

## Recipes

```
$ makoto-cli
Available recipes:
    default                                            # List available recipes
    fetch sources=(data_dir / "external/sources.yaml") # Fetch external datasets listed in sources.yaml
    gate mode="both"                                   # Run the full gate pipeline: discover → fetch → [auto-generate] → validate
    generate file *args                                # Generate origin attestation + DBOM for a data file
    generate-all                                       # Generate DBOMs for all data assets missing one
    lineage file                                       # Show DBOM lineage chain for an asset
    schema-check                                       # Validate the DBOM JSON schemas (requires jsonschema)
    status                                             # Show summary table of all assets and their DBOM status
    transform file *args                               # Transform a dataset and update DBOM lineage
    validate file                                      # Validate a single DBOM
    validate-all                                       # Validate all DBOMs in the dboms/ directory
    test                                               # Run the test suite
```

## Quick Start

```bash
# Generate an origin attestation + DBOM for a CSV file
makoto-cli generate data/my-dataset.csv

# Validate all DBOMs
makoto-cli validate-all

# Run the full gate pipeline (fetch → auto-generate → validate)
makoto-cli gate

# Show lineage for a dataset
makoto-cli lineage dboms/my-dataset.dbom.json

# Show status of all data assets
makoto-cli status
```

## What It Produces

### Origin Attestation (in-toto Statement v1)

```json
{
  "_type": "https://in-toto.io/Statement/v1",
  "subject": [{ "name": "dataset:my-dataset", "digest": { "sha256": "abc123..." } }],
  "predicateType": "https://makoto.dev/origin/v1",
  "predicate": {
    "origin": { "source": "file://data/my-dataset.csv", "sourceType": "file" },
    "collector": { "id": "https://github.com/makoto-project/makoto-cli" },
    "schema": { "format": "csv" }
  }
}
```

### DBOM Document

```json
{
  "dbomVersion": "1.0.0",
  "dataset": { "name": "my-dataset", "version": "1.0.0", "makotoLevel": "L1" },
  "sources": [{ "name": "my-dataset", "attestationRef": "attestations/my-dataset.origin.json" }],
  "transformations": []
}
```

## Testing

The test suite lives in `tests/` and covers all 16 recipes with isolated temp directories per test:

```bash
# Run all tests
makoto-cli test

# Or directly
just --justfile tests/Justfile all
```

Tests include: generate (CSV + JSON), validate (single + all), generate-all (skip existing), fetch, transform, status, lineage, gate (both + gate-only), tampered hash detection, schema validation, and missing-DBOM gating.

## Configuration

Override defaults via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DBOM_DATA_DIR` | `./data` | Data directory to scan |
| `DBOM_DBOMS_DIR` | `./dboms` | Output directory for DBOMs |
| `DBOM_ATTESTATIONS_DIR` | `./attestations` | Output directory for attestations |
| `DBOM_PYTHON` | `python3` | Python interpreter |

## Makoto Levels

This toolkit targets **Makoto L1** (Provenance Exists). See [usemakoto.dev/spec](https://usemakoto.dev/spec/) for the full specification.

| Level | Guarantee | Status |
|-------|-----------|--------|
| **L1** | Provenance Exists | ✓ Implemented |
| **L2** | Authentic Provenance (signed) | Roadmap |
| **L3** | Unforgeable Provenance (hardware-backed) | Future |

## License

MIT