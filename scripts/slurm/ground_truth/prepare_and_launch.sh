#!/bin/bash
set -eo pipefail
pushd "$(dirname "${BASH_SOURCE[0]}")" > /dev/null

source ../helper/multi_batch_job_header.sh

echo "Preparing job..."
cp "${BASE_DB_DIR}/master.sqlite" "${ACTUAL_DB_DIR}/initial.sqlite"

for i in "${JOBS_TO_RUN[@]}"; do
  echo "Launching job ${i}..."
  sbatch --job-name="accurate_ri_gt_${i}" -o "${ACTUAL_LOGS_DIR}/${i}.log" -e "${ACTUAL_LOGS_DIR}/${i}.log"\
   job.sh "${ACTUAL_DB_DIR}" "${i}" "${JOB_COUNT}"
done

popd > /dev/null