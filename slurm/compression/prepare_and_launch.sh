#!/bin/bash
set -eo pipefail
cd "$(dirname "$0")" || exit

CONTAINER_PATH="../../container.sif"

SKIP_TRAINING=0
if [[ $# -gt 0 ]]; then
  SKIP_TRAINING=1
fi

source ../helper/paths.sh
source ../helper/multi_batch_job_header.sh

module load cesga/system apptainer/1.2.3
apptainer exec "$CONTAINER_PATH" ./prepare.sh "$BASE_DB_DIR" "$ACTUAL_DB_DIR"


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

for i in "${JOBS_TO_RUN[@]}"; do
  echo "Launching job ${i}..."
  sbatch "${SBATCH_ARGS[@]}" --job-name="accurate_compression_${i}" \
    -o "${ACTUAL_LOGS_DIR}/${i}.log" -e "${ACTUAL_LOGS_DIR}/${i}.log" \
    compress_job.sh "${CONTAINER_PATH}" "${ACTUAL_DB_DIR}" "${SHARED_DIR}" "${i}" "${JOB_COUNT}"
done

