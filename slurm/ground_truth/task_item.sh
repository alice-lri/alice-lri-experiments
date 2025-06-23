#!/bin/bash
set -eo pipefail
source ../helper/paths.sh

CONDA_ENV_NAME=$1
DB_DIR=$2
TASK_INDEX=$3
TASK_COUNT=$4

source ../helper/prepare_task_item.sh

echo "Running task $TASK_INDEX of $TASK_COUNT..."
python populate_ground_truth_db.py "$TASK_INDEX" "$TASK_COUNT" \
  --db_path="${DB_FILE_PATH}" \
  --kitti_root="${KITTI_PATH}" \
  --durlar_root="${DURLAR_PATH}" 2>&1 | tee "${TRACE_FILE_PATH}"

touch "${SUCCESS_FILE_PATH}"