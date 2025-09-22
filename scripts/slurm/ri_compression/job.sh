#!/bin/bash
#SBATCH -J accurate_compression
#SBATCH -o logs/%j.log
#SBATCH -e logs/%j.log
#SBATCH -n 64
#SBATCH -c 1
#SBATCH -t 06:00:00
#SBATCH --mem-per-cpu=3G
set -eo pipefail

DB_DIR=$1
SHARED_DIR=$2
JOB_INDEX=$3
JOB_COUNT=$4
ARG_TYPE=$5

source ../../common/load_env.sh
module load $ALICE_LRI_HPC_MODULES

echo "Beginning job ${JOB_INDEX}..."

export PYTHONPATH="$ACCURATE_RI_PIP_DIR:$PYTHONPATH"
srun apptainer exec "$CONTAINER_PATH" ./task.sh "$DB_DIR" "$SHARED_DIR" "$JOB_INDEX" "$JOB_COUNT" "$ARG_TYPE"

echo "Job ${JOB_INDEX} finished."
touch "${DB_DIR}/job_${JOB_INDEX}.success"
