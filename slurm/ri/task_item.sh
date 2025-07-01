#!/bin/bash
set -eo pipefail

DB_DIR=$1
SHARED_DIR=$2
TASK_INDEX=$3
TASK_COUNT=$4

source ../helper/prepare_task_item.sh
source ../helper/paths.sh

echo "Running task $TASK_INDEX of $TASK_COUNT..."
python -u python/run_ri_experiment.py --mode batch \
  --phase=evaluate \
  --type=compression \
  --task_id="$TASK_INDEX" \
  --task_count="$TASK_COUNT" \
  --db_path="${DB_FILE_PATH}" \
  --kitti_root="${KITTI_PATH}" \
  --private_dir="${PRIVATE_DIR}" \
  --shared_dir="${SHARED_DIR}" 2>&1 | tee "${TRACE_FILE_PATH}"
  # optional add durlar_root to evaluate durlar as well

touch "${SUCCESS_FILE_PATH}"
