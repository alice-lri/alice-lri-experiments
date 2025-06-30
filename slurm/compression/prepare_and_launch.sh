#!/bin/bash
set -eo pipefail
cd "$(dirname "$0")" || exit

CONTAINER_PATH="../../container.sif"

source ../helper/paths.sh
source ../helper/multi_batch_job_header.sh

module load cesga/system apptainer/1.2.3
apptainer exec "$CONTAINER_PATH" ./prepare.sh "$BASE_DB_DIR" "$ACTUAL_DB_DIR"

SKIP_TRAINING=0
for arg in "$@"; do
  if [[ "$arg" == "--skip-training" ]]; then
    SKIP_TRAINING=1
    break
  fi
done

if [[ "$SKIP_TRAINING" -eq 0 ]]; then
    echo "Launching train job..."
    TRAIN_JOB_ID=$(sbatch --parsable --job-name="accurate_compression_train" \
      -o "${ACTUAL_LOGS_DIR}/train.log" -e "${ACTUAL_LOGS_DIR}/train.log" \
      train_job.sh "${CONTAINER_PATH}" "${ACTUAL_DB_DIR}" "${SHARED_DIR}")

    TRAIN_DEPENDENCY_ARG="--dependency=afterok:${TRAIN_JOB_ID}"
  else
    echo "Skipping training job as requested."
    TRAIN_DEPENDENCY_ARG=""
  fi

for i in "${JOBS_TO_RUN[@]}"; do
  echo "Launching job ${i}..."
  sbatch "${TRAIN_DEPENDENCY_ARG}" --job-name="accurate_compression_${i}" \
    -o "${ACTUAL_LOGS_DIR}/${i}.log" -e "${ACTUAL_LOGS_DIR}/${i}.log" \
    compress_job.sh "${CONTAINER_PATH}" "${ACTUAL_DB_DIR}" "${SHARED_DIR}" "${i}" "${JOB_COUNT}"
done

