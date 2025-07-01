#!/bin/bash
set -eo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")" || exit

CONTAINER_PATH="../../container.sif"

SKIP_TRAINING=0
if [[ $# -gt 0 ]]; then
  SKIP_TRAINING=1
fi

source ../helper/paths.sh
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

read -r -p "Rebuild and test (Y/n)? " REBUILD
REBUILD=${REBUILD:-y}
if [[ "$REBUILD" == [Yy] ]]; then
    module load cesga/system apptainer/1.2.3
    apptainer exec "$CONTAINER_PATH" ./prepare.sh "$BASE_DB_DIR" "$ACTUAL_DB_DIR"
fi

if [[ "$SKIP_TRAINING" -eq 0 ]]; then
  echo "Launching train job..."
  TRAIN_JOB_ID=$(sbatch --parsable --job-name="accurate_compression_train" \
    -o "${ACTUAL_LOGS_DIR}/train.log" -e "${ACTUAL_LOGS_DIR}/train.log" \
    train_job.sh "${CONTAINER_PATH}" "${ACTUAL_DB_DIR}" "${SHARED_DIR}")
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
  sbatch "${SBATCH_ARGS[@]}" --job-name="accurate_compression_${i}" \
    --mem-per-cpu="${MEM_PER_CPU}" -o "${ACTUAL_LOGS_DIR}/${i}.log" -e "${ACTUAL_LOGS_DIR}/${i}.log" \
    ri_job.sh "${CONTAINER_PATH}" "${ACTUAL_DB_DIR}" "${SHARED_DIR}" "${i}" "${JOB_COUNT}" "${ARG_TYPE}"
done

