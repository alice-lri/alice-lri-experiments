#!/bin/bash
set -eo pipefail

DB_DIR=$1
SHARED_DIR=$2
TASK_INDEX=$3
TASK_COUNT=$4
ARG_TYPE=$5

source ../helper/prepare_task_item.sh
source ../helper/paths.sh

DATASETS_ARGS=()
DATASETS_ARGS+=("--kitti_root=${KITTI_PATH}")
if [[ "${ARG_TYPE}" == "ri" ]]; then
  DATASETS_ARGS+=("--durlar_root=${DURLAR_PATH}")
fi

echo "Running task $TASK_INDEX of $TASK_COUNT..."
python -u python/run_ri_experiment.py --mode batch \
  --phase=evaluate \
  --type="${ARG_TYPE}" \
  --task_id="$TASK_INDEX" \
  --task_count="$TASK_COUNT" \
  --db_path="${DB_FILE_PATH}" \
  "${DATASETS_ARGS[@]}" \
  --private_dir="${PRIVATE_DIR}" \
  --shared_dir="${SHARED_DIR}" 2>&1 | tee "${TRACE_FILE_PATH}"
  # optional add durlar_root to evaluate durlar as well

touch "${SUCCESS_FILE_PATH}"
