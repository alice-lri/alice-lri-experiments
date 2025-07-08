#!/bin/bash
set -eo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")" || exit

source ../helper/paths.sh
source ../helper/multi_batch_job_header.sh

CONTAINER_PATH="../../container.sif"
SRC_PATH="../../accurate-ri"
EXECUTABLE_NAME="examples_sql"

module load cesga/system apptainer/1.2.3
# TODO refactor this monster at some point
apptainer exec "$CONTAINER_PATH" ../ri/prepare.sh "$BASE_DB_DIR" "$ACTUAL_DB_DIR" "intrinsics" false

jq -n \
  --arg db_dir "$ACTUAL_DB_DIR" \
  --arg durlar "$DURLAR_PATH" \
  --arg kitti "$KITTI_PATH" \
  '{
    db_dir: $db_dir,
    dataset_root_path: {
      durlar: $durlar,
      kitti: $kitti
    }
  }' > "${SRC_PATH}/build/examples/config.json"


for i in "${JOBS_TO_RUN[@]}"; do
  echo "Launching job ${i}..."
  sbatch --job-name="accurate_ri_${i}" -o "${ACTUAL_LOGS_DIR}/${i}.log" -e "${ACTUAL_LOGS_DIR}/${i}.log" \
   job.sh "${CONTAINER_PATH}" "${SRC_PATH}/build/examples/${EXECUTABLE_NAME}" "${ACTUAL_DB_DIR}" \
    "${i}" "${JOB_COUNT}"
done