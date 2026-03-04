# Directory containing this Justfile
root := justfile_directory()

# Invocation directory (where `just` was called from)
invdir := invocation_directory()

# Scripts directory
scripts := root / "scripts"

# Default directories (can be overridden via env vars)
data_dir := env("DBOM_DATA_DIR", invdir / "data")
dboms_dir := env("DBOM_DBOMS_DIR", invdir / "dboms")
attestations_dir := env("DBOM_ATTESTATIONS_DIR", invdir / "attestations")

# Python interpreter
python := env("DBOM_PYTHON", "python3")

# List available recipes
default:
    @just --list

# --- Schema ---

# Validate the DBOM JSON schemas (requires jsonschema)
schema-check:
    @echo "Checking schemas..."
    @for f in {{root}}/schema/*.schema.json; do \
        {{python}} -c "import json; json.load(open('$f'))" && echo "  ✓ $f" || echo "  ✗ $f"; \
    done

# --- Generate ---

# Generate origin attestation + DBOM for a data file
generate file *args:
    #!/usr/bin/env bash
    cd "{{invdir}}"
    {{python}} {{scripts}}/generate_dbom.py {{file}} \
        --attestations-dir {{attestations_dir}} \
        --dboms-dir {{dboms_dir}} \
        {{args}}

# Generate DBOMs for all data assets missing one
generate-all:
    #!/usr/bin/env bash
    set -euo pipefail
    found=0
    for f in $(find {{data_dir}} -type f \( -name '*.csv' -o -name '*.json' -o -name '*.parquet' \) 2>/dev/null | sort); do
        name="$(basename "${f%.*}")"
        if [ ! -f "{{dboms_dir}}/${name}.dbom.json" ]; then
            echo "Generating DBOM for ${f}..."
            {{python}} {{scripts}}/generate_dbom.py "$f" \
                --attestations-dir {{attestations_dir}} \
                --dboms-dir {{dboms_dir}}
            found=$((found + 1))
        fi
    done
    if [ "$found" -eq 0 ]; then
        echo "All data assets already have DBOMs."
    else
        echo "Generated ${found} new DBOM(s)."
    fi

# --- Validate ---

# Validate a single DBOM
validate file:
    #!/usr/bin/env bash
    cd "{{invdir}}"
    {{python}} {{scripts}}/validate_dbom.py {{file}}

# Validate all DBOMs in the dboms/ directory
validate-all:
    #!/usr/bin/env bash
    cd "{{invdir}}"
    {{python}} {{scripts}}/validate_dbom.py --all --dboms-dir {{dboms_dir}}

# --- Fetch ---

# Fetch external datasets listed in sources.yaml
fetch sources=(data_dir / "external/sources.yaml"):
    #!/usr/bin/env bash
    cd "{{invdir}}"
    {{python}} {{scripts}}/fetch_data.py {{sources}} \
        --output-dir {{data_dir}}/external

# --- Transform ---

# Transform a dataset and update DBOM lineage
transform file *args:
    #!/usr/bin/env bash
    cd "{{invdir}}"
    {{python}} {{scripts}}/transform_data.py {{file}} \
        --attestations-dir {{attestations_dir}} \
        {{args}}

# --- Gate ---

# Run the full gate pipeline: discover → fetch → [auto-generate] → validate
gate mode="both":
    #!/usr/bin/env bash
    set -euo pipefail
    echo "═══════════════════════════════════════"
    echo " DBOM Gate Pipeline (mode: {{mode}})"
    echo "═══════════════════════════════════════"
    echo ""

    # Step 1: Discover data assets
    echo "▸ Step 1: Discovering data assets..."
    assets=$(find {{data_dir}} -type f \( -name '*.csv' -o -name '*.json' -o -name '*.parquet' \) ! -name 'sources.yaml' 2>/dev/null | sort)
    count=$(echo "$assets" | grep -c . || true)
    echo "  Found ${count} data asset(s)"
    echo ""

    # Step 2: Fetch external datasets
    if [ -f "{{data_dir}}/external/sources.yaml" ]; then
        echo "▸ Step 2: Fetching external datasets..."
        {{python}} {{scripts}}/fetch_data.py {{data_dir}}/external/sources.yaml \
            --output-dir {{data_dir}}/external || true
        # Re-discover after fetch
        assets=$(find {{data_dir}} -type f \( -name '*.csv' -o -name '*.json' -o -name '*.parquet' \) ! -name 'sources.yaml' 2>/dev/null | sort)
        count=$(echo "$assets" | grep -c . || true)
        echo "  Total assets after fetch: ${count}"
        echo ""
    fi

    # Step 3: Auto-generate (if mode allows)
    if [ "{{mode}}" = "auto-generate" ] || [ "{{mode}}" = "both" ]; then
        echo "▸ Step 3: Auto-generating missing DBOMs..."
        gen_found=0
        for f in $(find {{data_dir}} -type f \( -name '*.csv' -o -name '*.json' -o -name '*.parquet' \) 2>/dev/null | sort); do
            name="$(basename "${f%.*}")"
            if [ ! -f "{{dboms_dir}}/${name}.dbom.json" ]; then
                echo "Generating DBOM for ${f}..."
                {{python}} {{scripts}}/generate_dbom.py "$f" \
                    --attestations-dir {{attestations_dir}} \
                    --dboms-dir {{dboms_dir}}
                gen_found=$((gen_found + 1))
            fi
        done
        if [ "$gen_found" -eq 0 ]; then
            echo "All data assets already have DBOMs."
        else
            echo "Generated ${gen_found} new DBOM(s)."
        fi
        echo ""
    else
        echo "▸ Step 3: Skipped (gate-only mode)"
        echo ""
    fi

    # Step 4: Validate all
    echo "▸ Step 4: Validating all DBOMs..."
    {{python}} {{scripts}}/validate_dbom.py --all --dboms-dir {{dboms_dir}}

# --- Info ---

# Show DBOM lineage chain for an asset
lineage file:
    #!/usr/bin/env bash
    cd "{{invdir}}"
    {{python}} {{scripts}}/lineage.py {{file}}

# Show summary table of all assets and their DBOM status
status:
    #!/usr/bin/env bash
    cd "{{invdir}}"
    {{python}} {{scripts}}/status.py {{data_dir}} {{dboms_dir}}
