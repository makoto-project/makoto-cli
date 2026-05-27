# `generate` — composite GitHub Action

Generate a Makoto DBOM (Data Bill of Materials, schema `v0.1`) for a data file
from inside a GitHub Actions workflow.

Wraps [`scripts/generate_dbom.py`](../../../scripts/generate_dbom.py), which
delegates to the [Makoto Python SDK](https://usemakoto.dev/sdk/python/).
You don't need to clone the `makoto-cli` repo or vendor anything — just
`uses:` the action.

## Usage

```yaml
- uses: actions/checkout@v4

- name: Generate DBOM for training data
  id: dbom
  uses: makoto-project/makoto-cli/.github/actions/generate@main
  with:
    file: data/training_set.csv

- name: Upload DBOM as artifact
  uses: actions/upload-artifact@v4
  with:
    name: dbom
    path: ${{ steps.dbom.outputs.dbom-path }}
```

## Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `file` | yes | — | Path to the data file |
| `dboms-dir` | no | `dboms` | Output dir for the DBOM document |
| `signer` | no | `github:<actor>` | Signer identity recorded in `signature.signer` |
| `uri` | no | `file://<path>` | Source URI recorded in `source.uri` |
| `format` | no | inferred | Data format recorded in `source.format` |
| `collector-id` | no | `https://github.com/<repo>` | Recorded in the lineage step `tool` field |
| `dataset-version` | no | `1.0.0` | Recorded in the lineage step description |
| `python-version` | no | `3.12` | Python version for `setup-python` |

## Outputs

| Output | Description |
|---|---|
| `dbom-path` | Path to the generated DBOM JSON file |
| `sha256` | SHA-256 of the data file (`source.hash.value`) |
| `signer` | Signer identity recorded in the DBOM (`signature.signer`) |

## What it produces

A single self-contained Makoto DBOM (v0.1) at
`dboms-dir/<name>.dbom.json`, conforming to
[`https://usemakoto.dev/schema/v0.1.json`](https://usemakoto.dev/schema/v0.1.json).

For the full pipeline (discover → fetch → auto-generate → validate), use
the `gate` recipe locally or clone the toolkit in CI:

```bash
git clone https://github.com/makoto-project/makoto-cli.git
just --justfile makoto-cli/Justfile install
just --justfile makoto-cli/Justfile gate both
```
