#!/bin/bash
set -eo pipefail
pushd "$(dirname "${BASH_SOURCE[0]}")" > /dev/null

source ../helper/multi_batch_job_header.sh

echo "Select experiment type:"
echo "[1] Range Image"
echo "[2] Compression"

read -r -p "Enter choice: " EXPERIMENT_TYPE

if [[ "$EXPERIMENT_TYPE" == "1" ]]; then
  ARG_TYPE="ri"
elif [[ "$EXPERIMENT_TYPE" == "2" ]]; then
  ARG_TYPE="compression"
else
  echo "Invalid choice."
  exit 1
fi

echo "Will use arg type=${ARG_TYPE}"

module load $ALICE_LRI_HPC_MODULES
apptainer run "$CONTAINER_PATH" ../helper/prepare_job.sh "$ACTUAL_DB_DIR" "$ARG_TYPE" "$REBUILD" "${BUILD_OPTIONS[*]}"

if [[ "$ARG_TYPE" == "ri" ]]; then
  BASE_JOB_NAME="alice_lri_ri"
elif [[ "$ARG_TYPE" == "compression" ]]; then
  BASE_JOB_NAME="alice_lri_compression"
else
  echo "Unknown argument type: $ARG_TYPE"
  exit 1
fi

if [[ "$SKIP_ESTIMATION" == false ]]; then
  echo "Launching intrinsics estimation job..."
  ESTIMATE_JOB_ID=$(sbatch --parsable --job-name="${BASE_JOB_NAME}_estimate" \
    -o "${ACTUAL_LOGS_DIR}/estimate.log" -e "${ACTUAL_LOGS_DIR}/estimate.log" \
    estimate_job.sh "${ACTUAL_DB_DIR}" "${SHARED_DIR}" "${ARG_TYPE}")
    echo "Submitted batch job ${ESTIMATE_JOB_ID}"
else
  echo "Skipping intrinsics estimation job as requested."
fi

SBATCH_ARGS=()
if [[ -n "$ESTIMATE_JOB_ID" ]]; then
  SBATCH_ARGS+=("--dependency=afterok:${ESTIMATE_JOB_ID}")
fi

if [ "$ARG_TYPE" == "ri" ]; then
    MEM_PER_CPU="12G"
elif [ "$ARG_TYPE" == "compression" ]; then
    MEM_PER_CPU="3G"
fi

for i in "${JOBS_TO_RUN[@]}"; do
  echo "Launching job ${i}..."
  sbatch "${SBATCH_ARGS[@]}" --job-name="${BASE_JOB_NAME}_${i}" \
    --mem-per-cpu="${MEM_PER_CPU}" -o "${ACTUAL_LOGS_DIR}/${i}.log" -e "${ACTUAL_LOGS_DIR}/${i}.log" \
    job.sh "${ACTUAL_DB_DIR}" "${SHARED_DIR}" "${i}" "${JOB_COUNT}" "${ARG_TYPE}"
done

popd > /dev/null
