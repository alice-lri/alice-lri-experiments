#!/bin/bash
#SBATCH -J accurate_compression
#SBATCH -o logs/%j.log
#SBATCH -e logs/%j.log
#SBATCH -n 64
#SBATCH -c 1
#SBATCH -t 06:00:00
#SBATCH --mem-per-cpu=3G
#SBATCH --mail-type=begin
#SBATCH --mail-type=end
#SBATCH --mail-user=s.soutullo@usc.es
set -eo pipefail

CONTAINER_PATH=$1
DB_DIR=$2
SHARED_DIR=$3
JOB_INDEX=$4
JOB_COUNT=$5

source ../helper/paths.sh
module load cesga/system apptainer/1.2.3

echo "Beginning job ${JOB_INDEX}..."

export PYTHONPATH="$ACCURATE_RI_PIP_DIR:$PYTHONPATH"
srun apptainer exec "$CONTAINER_PATH" ./task.sh "$DB_DIR" "$SHARED_DIR" "$JOB_INDEX" "$JOB_COUNT"

echo "Job ${JOB_INDEX} finished."
touch "${DB_DIR}/job_${JOB_INDEX}.success"
