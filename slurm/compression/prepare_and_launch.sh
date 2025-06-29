#!/bin/bash
set -eo pipefail
cd "$(dirname "$0")" || exit

CONTAINER_PATH="../../container.sif"

source ../helper/paths.sh
source ../helper/multi_batch_job_header.sh

module load cesga/system apptainer/1.2.3
apptainer exec "$CONTAINER_PATH" ./prepare.sh "$BASE_DB_DIR" "$ACTUAL_DB_DIR"

# TODO probably skip this if recontinuing previous job
echo "Launching train job..."
TRAIN_JOB_ID=$(sbatch --parsable --job-name="accurate_compression_train" \
  -o "${ACTUAL_LOGS_DIR}/train.log" -e "${ACTUAL_LOGS_DIR}/train.log" \
  train_job.sh "${CONTAINER_PATH}" "${ACTUAL_DB_DIR}" "${SHARED_DIR}")

for i in "${JOBS_TO_RUN[@]}"; do
  echo "Launching job ${i}..."
  sbatch --dependency=afterok:"${TRAIN_JOB_ID}" --job-name="accurate_compression_${i}" \
    -o "${ACTUAL_LOGS_DIR}/${i}.log" -e "${ACTUAL_LOGS_DIR}/${i}.log" \
    compress_job.sh "${CONTAINER_PATH}" "${ACTUAL_DB_DIR}" "${SHARED_DIR}" "${i}" "${JOB_COUNT}"
done

