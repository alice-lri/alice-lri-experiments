#!/bin/bash
set -eo pipefail

DB_DIR=$1
TASK_INDEX=$2
TASK_COUNT=$3

source ../helper/prepare_task_item.sh

echo "Running local-geometry task $TASK_INDEX of $TASK_COUNT..."
pushd "${PROJECT_ROOT}" > /dev/null
python -u -m scripts.slurm.local_geometry.run_local_geometry_experiment --mode batch \
  --task_id="$TASK_INDEX" \
  --task_count="$TASK_COUNT" \
  --db_path="${DB_FILE_PATH}" \
  --kitti_root="${KITTI_PATH}" \
  --durlar_root="${DURLAR_PATH}" \
  --k_neighbors=12 \
  --methods alice_lri pbea_native 2>&1 | tee "${TRACE_FILE_PATH}"
popd > /dev/null

touch "${SUCCESS_FILE_PATH}"
