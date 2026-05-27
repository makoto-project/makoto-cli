# makoto-cli

A CLI toolkit for generating, validating, and managing [Makoto](https://usemakoto.dev) **Data Bills of Materials (DBOMs)** — provenance records that prove where your data came from and how it was transformed.

Built as a [Justfile](https://github.com/casey/just) following the [makoto-project/justfiles](https://github.com/makoto-project/justfiles) pattern: clone it, alias it, use it from anywhere. Under the hood, every recipe delegates to the [Makoto Python SDK](https://usemakoto.dev/sdk/python/) (`makoto` on PyPI/git).

## Install

```bash
# Prerequisites: just, python3, pip
# macOS
brew install just

# Clone and alias
git clone https://github.com/makoto-project/makoto-cli.git ~/makoto-cli
echo "alias makoto-cli='just --justfile ~/makoto-cli/Justfile'" >> ~/.bashrc
source ~/.bashrc

# Install the Makoto Python SDK (one-time)
makoto-cli install
```

`makoto-cli install` runs `pip install -r requirements.txt`, which pulls the
[`makoto`](https://usemakoto.dev/sdk/python/) Python SDK from the
`makoto-project/usemakoto.dev` repository.

## Recipes

```
$ makoto-cli
Available recipes:
    default                                            # List available recipes
    fetch sources=(data_dir / "external/sources.yaml") # Fetch external datasets listed in sources.yaml
    gate mode="both"                                   # Run the full gate pipeline: discover → fetch → [auto-generate] → validate
    generate file *args                                # Generate a Makoto DBOM (v0.1) for a data file
    generate-all                                       # Generate DBOMs for all data assets missing one
    install                                            # Install the Makoto Python SDK and any other dependencies
    lineage file                                       # Show DBOM lineage chain for an asset
    schema-check                                       # Validate the bundled DBOM JSON schema (requires python stdlib only)
    status                                             # Show summary table of all assets and their DBOM status
    transform file *args                               # Transform a dataset and write a new DBOM with chained lineage
    validate file                                      # Validate a single DBOM
    validate-all                                       # Validate all DBOMs in the dboms/ directory
    test                                               # Run the test suite
```

## Quick Start

```bash
# Generate a DBOM for a CSV file
makoto-cli generate data/my-dataset.csv

# Validate all DBOMs
makoto-cli validate-all

# Run the full gate pipeline (fetch → auto-generate → validate)
makoto-cli gate

# Show lineage for a dataset
makoto-cli lineage dboms/my-dataset.dbom.json

# Show status of all data assets
makoto-cli status

# Transform a dataset and chain the lineage in the new DBOM
makoto-cli transform data/my-dataset.csv --column value --operator '>' --value 100
```

## What It Produces

A single, self-contained **Makoto DBOM (v0.1)** per asset, conforming to
[`https://usemakoto.dev/schema/v0.1.json`](https://usemakoto.dev/schema/v0.1.json):

```json
{
  "schema_version": "0.1",
  "id": "dbom-3f2c8a4b-...",
  "created_at": "2026-05-27T10:30:00Z",
  "source": {
    "uri": "file:///data/my-dataset.csv",
    "hash": { "algorithm": "sha256", "value": "a1b2c3d4..." },
    "format": "csv"
  },
  "signature": {
    "algorithm": "sha256",
    "value": "e5f6a7b8...",
    "signer": "github:makoto-cli"
  },
  "lineage": [
    {
      "step": 1,
      "description": "Direct ingestion (dataset version 1.0.0)",
      "tool": "makoto-cli (https://github.com/makoto-project/makoto-cli)",
      "input_hash": "n/a",
      "output_hash": "a1b2c3d4..."
    }
  ]
}
```

`transform` recipes append additional `lineage[]` steps, so the chain travels
with the data.

## Testing

The test suite lives in `tests/` and covers all recipes with isolated temp
directories per test:

```bash
# Run all tests
makoto-cli test

# Or directly
just --justfile tests/Justfile all
```

Tests include: generate (CSV + JSON), validate (single + all), generate-all
(skip existing), fetch, transform with chained lineage, status, lineage,
gate (both + gate-only), tampered hash detection, schema validation, and
missing-DBOM gating.

## GitHub Action

Use makoto-cli from any workflow without cloning the repo via the composite
action at [`.github/actions/generate`](.github/actions/generate/):

```yaml
- uses: actions/checkout@v4
- uses: makoto-project/makoto-cli/.github/actions/generate@main
  with:
    file: data/training_set.csv
```

See the [action README](.github/actions/generate/README.md) for all inputs and outputs.

## Configuration

Override defaults via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DBOM_DATA_DIR` | `./data` | Data directory to scan |
| `DBOM_DBOMS_DIR` | `./dboms` | Output directory for DBOMs |
| `DBOM_PYTHON` | `python3` | Python interpreter |
| `MAKOTO_SIGNER` | `github:makoto-cli` | Default signer identity recorded in `signature.signer` |

## Makoto Levels

This toolkit targets **Makoto L1** (Provenance Exists). See [usemakoto.dev/spec](https://usemakoto.dev/spec/) for the full specification.

| Level | Guarantee | Status |
|-------|-----------|--------|
| **L1** | Provenance Exists | ✓ Implemented |
| **L2** | Authentic Provenance (signed) | Roadmap |
| **L3** | Unforgeable Provenance (hardware-backed) | Future |

## Architecture

```
makoto-cli
├── Justfile              # CLI entrypoint (just recipes)
├── requirements.txt      # Pins the makoto SDK
├── schema/v0.1.json      # Bundled DBOM schema (mirrors the SDK's)
├── scripts/              # Thin wrappers around `makoto.generate()` / `makoto.verify()`
│   ├── generate_dbom.py
│   ├── validate_dbom.py
│   ├── transform_data.py
│   ├── fetch_data.py
│   ├── status.py
│   └── lineage.py
├── tests/                # Justfile-driven integration tests
└── .github/actions/      # Composite GitHub Action
```

## License

MIT
