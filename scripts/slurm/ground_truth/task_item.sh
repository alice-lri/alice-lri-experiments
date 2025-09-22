#!/bin/bash
set -eo pipefail

DB_DIR=$1
TASK_INDEX=$2
TASK_COUNT=$3

source ../helper/prepare_task_item.sh

echo "Running task $TASK_INDEX of $TASK_COUNT..."
python populate_ground_truth_db.py "$TASK_INDEX" "$TASK_COUNT" --db_path="${DB_FILE_PATH}" | tee "${TRACE_FILE_PATH}"

touch "${SUCCESS_FILE_PATH}"
