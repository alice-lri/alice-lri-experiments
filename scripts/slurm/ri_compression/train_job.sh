#!/bin/bash
#SBATCH -J accurate_compression
#SBATCH -o logs/%j.log
#SBATCH -e logs/%j.log
#SBATCH -n 1
#SBATCH -c 1
#SBATCH -t 06:00:00
#SBATCH --mem-per-cpu=3G
set -eo pipefail

DB_DIR=$1
SHARED_DIR=$2
ARG_TYPE=$3

source ../../common/load_env.sh
module load $ALICE_LRI_HPC_MODULES

echo "Beginning train job..."

export PYTHONPATH="$ACCURATE_RI_PIP_DIR:$PYTHONPATH"
srun apptainer exec "$CONTAINER_PATH" \
 python -u python/run_ri_experiment.py --mode batch \
 --phase=train \
 --type="${ARG_TYPE}" \
 --db_path="${DB_DIR}/initial.sqlite" \
 --kitti_root="${KITTI_PATH}" \
 --durlar_root="${DURLAR_PATH}" \
 --private_dir="${TMPDIR}" \
 --shared_dir="${SHARED_DIR}"

echo "Train job finished."
touch "${DB_DIR}/train_job.success"
