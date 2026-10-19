#!/usr/bin/env bash
# Sets up the project's dependencies (see "Project Setup" in CLAUDE.md).
#
# Usage:
#   source setup.sh   # sets up and leaves .venv active in your current shell
#   bash setup.sh     # sets up only; run "source .venv/bin/activate" afterwards

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"

# Stop on error without closing the terminal when the script is sourced
fail() {
    echo "Setup failed: $1"
    return 1 2>/dev/null || exit 1
}

# 1. Create a python virtual environment .venv
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    echo "Creating virtual environment in .venv"
    python3 -m venv "$PROJECT_DIR/.venv" || fail "could not create .venv" || return 1 2>/dev/null
else
    echo ".venv already exists, skipping creation"
fi

# 2. Activate the env
source "$PROJECT_DIR/.venv/bin/activate" || fail "could not activate .venv" || return 1 2>/dev/null

# 3. Install packages from requirements.txt
echo "Installing packages from requirements.txt"
pip install -r "$PROJECT_DIR/requirements.txt" || fail "pip install failed" || return 1 2>/dev/null

# 4. Create .env file with the Census API key (required)
ENV_FILE="$PROJECT_DIR/.env"
if [ -f "$ENV_FILE" ] && grep -q "^CENSUS_API_KEY=..*" "$ENV_FILE"; then
    echo ".env already has CENSUS_API_KEY, leaving it unchanged"
else
    echo "A Census API key is required. Request one at: https://api.census.gov/data/key_signup.html"
    census_key=""
    while [ -z "$census_key" ]; do
        printf "Enter your Census API key (or q to stop setup): "
        read -r census_key || census_key="q"   # treat end of input as stop
        if [ "$census_key" = "q" ] || [ "$census_key" = "Q" ]; then
            echo "Setup stopped. Run it again once you have your API key."
            return 1 2>/dev/null || exit 1
        fi
        [ -z "$census_key" ] && echo "API key cannot be empty."
    done

    # Drop any existing empty CENSUS_API_KEY line before writing the new one
    if [ -f "$ENV_FILE" ]; then
        grep -v "^CENSUS_API_KEY=" "$ENV_FILE" > "$ENV_FILE.tmp"
        mv "$ENV_FILE.tmp" "$ENV_FILE"
    fi
    echo "CENSUS_API_KEY=${census_key}" >> "$ENV_FILE"
    echo "Saved CENSUS_API_KEY to .env"
fi

# 5. Remove the existing database so it is rebuilt from database/DDL.sql
DB_FILE="$PROJECT_DIR/database/covid.db"
if [ -f "$DB_FILE" ]; then
    rm -f "$DB_FILE"
    echo "Removed existing database/covid.db"
fi

echo "Setup complete."
