#!/bin/bash
set -eo pipefail
pushd "$(dirname "${BASH_SOURCE[0]}")" > /dev/null

source ../helper/multi_batch_job_header.sh

module load $ALICE_LRI_HPC_MODULES
apptainer run "$CONTAINER_PATH" ../helper/prepare_job.sh "$ACTUAL_DB_DIR" "local_geometry" "$REBUILD" "${BUILD_OPTIONS[*]}"

if [[ "$SKIP_ESTIMATION" == false ]]; then
  echo "Launching local-geometry intrinsics estimation job..."
  ESTIMATE_JOB_ID=$(sbatch --parsable --job-name="alice_lri_local_geometry_estimate" \
    -o "${ACTUAL_LOGS_DIR}/estimate.log" -e "${ACTUAL_LOGS_DIR}/estimate.log" \
    estimate_job.sh "${ACTUAL_DB_DIR}" "${SHARED_DIR}")
  echo "Submitted batch job ${ESTIMATE_JOB_ID}"
else
  echo "Skipping local-geometry intrinsics estimation job as requested."
fi

SBATCH_ARGS=()
if [[ -n "$ESTIMATE_JOB_ID" ]]; then
  SBATCH_ARGS+=("--dependency=afterok:${ESTIMATE_JOB_ID}")
fi

for i in "${JOBS_TO_RUN[@]}"; do
  echo "Launching job ${i}..."
  sbatch "${SBATCH_ARGS[@]}" --job-name="alice_lri_local_geometry_${i}" \
    --mem-per-cpu="3G" -o "${ACTUAL_LOGS_DIR}/${i}.log" -e "${ACTUAL_LOGS_DIR}/${i}.log" \
    job.sh "${ACTUAL_DB_DIR}" "${SHARED_DIR}" "${i}" "${JOB_COUNT}"
done

popd > /dev/null
