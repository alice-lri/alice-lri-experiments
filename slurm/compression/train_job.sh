#!/bin/bash
#SBATCH -J accurate_compression
#SBATCH -o logs/%j.log
#SBATCH -e logs/%j.log
#SBATCH -n 1
#SBATCH -c 1
#SBATCH -t 06:00:00
#SBATCH --mem-per-cpu=16G
#SBATCH --mail-type=begin
#SBATCH --mail-type=end
#SBATCH --mail-user=s.soutullo@usc.es
set -eo pipefail

CONTAINER_PATH=$1
DB_DIR=$2
SHARED_DIR=$3

source ../helper/paths.sh
module load cesga/system apptainer/1.2.3

echo "Beginning train job..."

export PYTHONPATH="$ACCURATE_RI_PIP_DIR:$PYTHONPATH"
srun apptainer exec "$CONTAINER_PATH" \
python run_compression_experiment.py --mode batch \
 --phase train \
 --db_path="${DB_DIR}/initial.sqlite" \
 --kitti_root="${KITTI_PATH}" \
 --private_dir "${TMPDIR}" \
 --shared_dir "${SHARED_DIR}"
 # optional add durlar_root to evaluate durlar as well

echo "Train job finished."
touch "${DB_DIR}/train_job.success"
