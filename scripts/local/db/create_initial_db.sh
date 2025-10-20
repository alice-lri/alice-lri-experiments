#!/bin/bash
set -eo pipefail
pushd "$(dirname "${BASH_SOURCE[0]}")" > /dev/null

source ../../common/load_env.sh

pushd "$PROJECT_ROOT" > /dev/null

if [ -f "$LOCAL_SQLITE_INITIAL_DB" ]; then
    echo "Initial database already exists at $LOCAL_SQLITE_INITIAL_DB, skipping creation."
else
    echo "Creating initial database at $LOCAL_SQLITE_INITIAL_DB..."
    TEMP_DB="${LOCAL_SQLITE_INITIAL_DB}.tmp"
    
    trap "rm -f '$TEMP_DB'" EXIT
    
    sqlite3 "$TEMP_DB" < scripts/local/db/helper/experiments_db.sql
    python -m scripts.local.db.helper.populate_db_base_entities
    mv "$TEMP_DB" "$LOCAL_SQLITE_INITIAL_DB"
    
    trap - EXIT
    
    echo "Initial database created successfully."
fi

popd > /dev/null
popd > /dev/null
