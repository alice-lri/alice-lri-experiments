#!/bin/bash
set -eo pipefail

DB_DIR=$1
TASK_INDEX=$2
TASK_COUNT=$3

source ../helper/prepare_task_item.sh

echo "Running task $TASK_INDEX of $TASK_COUNT..."
pushd "${PROJECT_ROOT}" > /dev/null
python -m scripts.slurm.ground_truth.populate_ground_truth_db "$TASK_INDEX" "$TASK_COUNT" --db_path="${DB_FILE_PATH}" | tee "${TRACE_FILE_PATH}"
popd > /dev/null

touch "${SUCCESS_FILE_PATH}"
