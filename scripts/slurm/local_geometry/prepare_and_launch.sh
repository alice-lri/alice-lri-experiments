#!/bin/bash
set -eo pipefail
pushd "$(dirname "${BASH_SOURCE[0]}")" > /dev/null

source ../helper/multi_batch_job_header.sh

module load $ALICE_LRI_HPC_MODULES
apptainer run "$CONTAINER_PATH" ../helper/prepare_job.sh "$ACTUAL_DB_DIR" "local_geometry" "$REBUILD" "${BUILD_OPTIONS[*]}"

for i in "${JOBS_TO_RUN[@]}"; do
  echo "Launching job ${i}..."
  sbatch --job-name="alice_lri_local_geometry_${i}" \
    --mem-per-cpu="3G" -o "${ACTUAL_LOGS_DIR}/${i}.log" -e "${ACTUAL_LOGS_DIR}/${i}.log" \
    job.sh "${ACTUAL_DB_DIR}" "${i}" "${JOB_COUNT}"
done

popd > /dev/null
