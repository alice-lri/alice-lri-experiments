#!/bin/bash
set -eo pipefail
pushd "$(dirname "${BASH_SOURCE[0]}")" > /dev/null

source ../helper/multi_batch_job_header.sh

module load $ALICE_LRI_HPC_MODULES
apptainer run "$CONTAINER_PATH" ../helper/prepare_job.sh "$ACTUAL_DB_DIR" "intrinsics" "$REBUILD" "${BUILD_OPTIONS[*]}"

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
  }' > "$INTRINSICS_SQL_CONFIG_JSON_PATH"


for i in "${JOBS_TO_RUN[@]}"; do
  echo "Launching job ${i}..."
  sbatch --job-name="alice_lri_${i}" -o "${ACTUAL_LOGS_DIR}/${i}.log" -e "${ACTUAL_LOGS_DIR}/${i}.log" \
   job.sh "${ACTUAL_DB_DIR}" "${i}" "${JOB_COUNT}"
done

popd > /dev/null