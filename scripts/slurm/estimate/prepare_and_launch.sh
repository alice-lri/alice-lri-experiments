#!/bin/bash
set -eo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")" || exit

source ../../common/load_env.sh
source ../helper/multi_batch_job_header.sh

module load cesga/system apptainer/1.2.3
apptainer exec "$CONTAINER_PATH" ../helper/prepare_job.sh "$ACTUAL_DB_DIR" "intrinsics" "$REBUILD" "${BUILD_OPTIONS[*]}"

# TODO maybe do not use this whole json thing (env instead)
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
   job.sh "${ACTUAL_DB_DIR}" "${i}" "${JOB_COUNT}"
done