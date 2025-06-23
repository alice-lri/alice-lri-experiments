#!/bin/bash
set -eo pipefail

CONDA_ENV_NAME=$1
EXECUTABLE_PATH=$2
DB_DIR=$3
TASK_INDEX=$4
TASK_COUNT=$5

EXEC_DIR=$(dirname "$EXECUTABLE_PATH")
EXEC_FILE=$(basename "$EXECUTABLE_PATH")

cd "$EXEC_DIR" || { echo "Failed to cd into $EXEC_DIR"; exit 1; }

source ../helper/prepare_task_item.sh

echo "Running task $TASK_INDEX of $TASK_COUNT..."
python run_compression_experiment.py --mode batch \
  --task_id "$TASK_INDEX" \
  --task_count "$TASK_COUNT" \
  --db_path="${DB_FILE_PATH}" \
  --kitti_root="${KITTI_PATH}" \
  --durlar_root="${DURLAR_PATH}" 2>&1 | tee "${TRACE_FILE_PATH}"

touch "${SUCCESS_FILE_PATH}"