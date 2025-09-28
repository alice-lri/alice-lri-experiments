#!/bin/bash
#SBATCH -J alice_lri_gt
#SBATCH -o logs/%j.log
#SBATCH -e logs/%j.log
#SBATCH -n 64
#SBATCH -c 1
#SBATCH -t 06:00:00
#SBATCH --mem-per-cpu=3G
set -eo pipefail
pushd "$(dirname "${BASH_SOURCE[0]}")" > /dev/null

DB_DIR=$1
JOB_INDEX=$2
JOB_COUNT=$3

source ../../common/load_env.sh
module load $ALICE_LRI_HPC_MODULES

echo "Beginning job ${JOB_INDEX}..."

export PYTHONPATH="$ALICE_LRI_PIP_DIR:$PYTHONPATH"
srun apptainer run "$CONTAINER_PATH" ./task.sh "$DB_DIR" "$JOB_INDEX" "$JOB_COUNT"

echo "Job ${JOB_INDEX} finished."
touch "${DB_DIR}/job_${JOB_INDEX}.success"

popd > /dev/null
