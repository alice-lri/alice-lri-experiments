#!/bin/bash
#SBATCH -J local_geometry
#SBATCH -o logs/%j.log
#SBATCH -e logs/%j.log
#SBATCH -n 64
#SBATCH --ntasks-per-node=16
#SBATCH -c 1
#SBATCH -t 06:00:00
#SBATCH --mem-per-cpu=12G
set -eo pipefail

DB_DIR=$1
SHARED_DIR=$2
JOB_INDEX=$3
JOB_COUNT=$4

source ../../common/load_env.sh
module load $ALICE_LRI_HPC_MODULES

echo "Beginning local-geometry job ${JOB_INDEX}..."

export PYTHONPATH="$ALICE_LRI_PIP_DIR:$PYTHONPATH"
srun apptainer run "$CONTAINER_PATH" ./task.sh "$DB_DIR" "$SHARED_DIR" "$JOB_INDEX" "$JOB_COUNT"

echo "Local-geometry job ${JOB_INDEX} finished."
touch "${DB_DIR}/job_${JOB_INDEX}.success"
