#!/bin/bash
set -eo pipefail

CONDA_ENV_NAME=$1
DB_DIR=$2
SHARED_DIR=$3
TASK_INDEX=$4
TASK_COUNT=$5

source ../helper/prepare_task_item.sh

echo "Running task $TASK_INDEX of $TASK_COUNT..."
python run_compression_experiment.py --mode batch \
  --phase compression \
  --task_id "$TASK_INDEX" \
  --task_count "$TASK_COUNT" \
  --db_path="${DB_FILE_PATH}" \
  --kitti_root="${KITTI_PATH}" \
  --private_dir "${TMPDIR}" \
  --shared_dir "${SHARED_DIR}" 2>&1 | tee "${TRACE_FILE_PATH}"
  # optional add durlar_root to evaluate durlar as well

touch "${SUCCESS_FILE_PATH}"
