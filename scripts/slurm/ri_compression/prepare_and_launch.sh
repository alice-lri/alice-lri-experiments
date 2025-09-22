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
apptainer exec "$CONTAINER_PATH" ./prepare.sh "$BASE_DB_DIR" "$ACTUAL_DB_DIR" "$ARG_TYPE" "$REBUILD" "${BUILD_OPTIONS[*]}"

if [[ "$ARG_TYPE" == "ri" ]]; then
  BASE_JOB_NAME="accurate_ri"
elif [[ "$ARG_TYPE" == "compression" ]]; then
  BASE_JOB_NAME="accurate_compression"
else
  echo "Unknown argument type: $ARG_TYPE"
  exit 1
fi

if [[ "$SKIP_TRAINING" == false ]]; then
  echo "Launching train job..."
  TRAIN_JOB_ID=$(sbatch --parsable --job-name="${BASE_JOB_NAME}_train" \
    -o "${ACTUAL_LOGS_DIR}/train.log" -e "${ACTUAL_LOGS_DIR}/train.log" \
    train_job.sh "${CONTAINER_PATH}" "${ACTUAL_DB_DIR}" "${SHARED_DIR}" "${ARG_TYPE}")
    echo "Submitted batch job ${TRAIN_JOB_ID}"
else
  echo "Skipping training job as requested."
fi

SBATCH_ARGS=()
if [[ -n "$TRAIN_JOB_ID" ]]; then
  SBATCH_ARGS+=("--dependency=afterok:${TRAIN_JOB_ID}")
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
