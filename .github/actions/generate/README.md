# `generate` — composite GitHub Action

Generate a Makoto DBOM (Data Bill of Materials) and its in-toto Statement v1
origin attestation for a data file, from inside a GitHub Actions workflow.

Wraps [`scripts/generate_dbom.py`](../../../scripts/generate_dbom.py) so you
don't need to clone the `makoto-cli` repo or vendor the toolkit — just `uses:`
the action.

## Usage

```yaml
- uses: actions/checkout@v4

- name: Generate DBOM for training data
  id: dbom
  uses: makoto-project/makoto-cli/.github/actions/generate@main
  with:
    file: data/training_set.csv

- name: Upload DBOM + attestation as artifacts
  uses: actions/upload-artifact@v4
  with:
    name: dbom
    path: |
      ${{ steps.dbom.outputs.dbom-path }}
      ${{ steps.dbom.outputs.attestation-path }}
```

## Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `file` | yes | — | Path to the data file |
| `attestations-dir` | no | `attestations` | Output dir for the origin attestation |
| `dboms-dir` | no | `dboms` | Output dir for the DBOM document |
| `source-type` | no | `file` | Source type recorded in the origin predicate |
| `geography` | no | — | Geographic region (e.g. `US-WEST-2`) |
| `collector-id` | no | `https://github.com/<repo>` | Collector identifier URI |
| `dataset-version` | no | `1.0.0` | Dataset version |
| `python-version` | no | `3.12` | Python version for `setup-python` |

## Outputs

| Output | Description |
|---|---|
| `dbom-path` | Path to the generated DBOM JSON file |
| `attestation-path` | Path to the generated origin attestation JSON file |
| `sha256` | SHA-256 of the data file |

## What it produces

The action runs `scripts/generate_dbom.py`, which produces:

- **Origin attestation** — `in-toto Statement v1` with predicate type
  `https://makoto.dev/origin/v1`, written to `attestations-dir/<name>.origin.json`.
- **DBOM document** — Makoto L1 aggregate referencing the attestation,
  written to `dboms-dir/<name>.dbom.json`.

For the full pipeline (discover → fetch → auto-generate → validate), use
the `gate` recipe locally or clone the toolkit in CI:

```bash
git clone https://github.com/makoto-project/makoto-cli.git
just --justfile makoto-cli/Justfile gate both
```
