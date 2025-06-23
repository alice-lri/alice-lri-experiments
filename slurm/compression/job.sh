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

CONDA_ENV_NAME=$1
DB_DIR=$2
SHARED_DIR=$3
JOB_INDEX=$4
JOB_COUNT=$5

echo "Beginning job ${JOB_INDEX}..."

module load cesga/system miniconda3/22.11.1-1 cesga/2020 gcc/system openmpi/4.1.1_ft3 boost/1.79.0
conda activate "${CONDA_ENV_NAME}"

python run_compression_experiment.py --mode batch \
  --phase train \
  --db_path="${DB_FILE_PATH}" \
  --kitti_root="${KITTI_PATH}" \
  --private_dir "${TMPDIR}" \
  --shared_dir "${SHARED_DIR}" 2>&1 | tee "${TRACE_FILE_PATH}"
  # optional add durlar_root to evaluate durlar as well

srun task.sh "$CONDA_ENV_NAME" "$DB_DIR" "$SHARED_DIR" "$JOB_INDEX" "$JOB_COUNT"

echo "Job ${JOB_INDEX} finished."
touch "${DB_DIR}/job_${JOB_INDEX}.success"
