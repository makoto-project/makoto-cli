# dbom

A CLI toolkit for generating, validating, and managing [Makoto](https://usemakoto.dev) **Data Bills of Materials (DBOMs)** — signed attestations that prove where your data came from and how it was transformed.

Built as a [Justfile](https://github.com/casey/just) following the [asw101/justfiles](https://github.com/asw101/justfiles) pattern: clone it, alias it, use it from anywhere.

## Install

```bash
# Prerequisites: just, python3
# macOS
brew install just

# Clone and alias
git clone https://github.com/asw101/dbom.git ~/dbom
echo "alias dbom='just --justfile ~/dbom/Justfile'" >> ~/.bashrc
source ~/.bashrc
```

## Recipes

```
$ dbom
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
```

## Quick Start

```bash
# Generate an origin attestation + DBOM for a CSV file
dbom generate data/my-dataset.csv

# Validate all DBOMs
dbom validate-all

# Run the full gate pipeline (fetch → auto-generate → validate)
dbom gate

# Show lineage for a dataset
dbom lineage dboms/my-dataset.dbom.json

# Show status of all data assets
dbom status
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
    "collector": { "id": "https://github.com/asw101/dbom" },
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