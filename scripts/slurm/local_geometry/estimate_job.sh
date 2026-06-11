#!/bin/bash
#SBATCH -J local_geometry_estimate
#SBATCH -o logs/%j.log
#SBATCH -e logs/%j.log
#SBATCH -n 1
#SBATCH -c 1
#SBATCH -t 06:00:00
#SBATCH --mem-per-cpu=3G
set -eo pipefail

DB_DIR=$1
SHARED_DIR=$2

source ../../common/load_env.sh
module load $ALICE_LRI_HPC_MODULES

echo "Beginning local-geometry intrinsics estimation job..."

export PYTHONPATH="$ALICE_LRI_PIP_DIR:$PYTHONPATH"

pushd "$PROJECT_ROOT" > /dev/null
srun apptainer run "$CONTAINER_PATH" \
 python -u -m scripts.slurm.local_geometry.run_local_geometry_experiment --mode batch \
 --phase=estimate \
 --db_path="${DB_DIR}/initial.sqlite" \
 --kitti_root="${KITTI_PATH}" \
 --durlar_root="${DURLAR_PATH}" \
 --shared_dir="${SHARED_DIR}"
popd > /dev/null

echo "Local-geometry intrinsics estimation job finished."
touch "${DB_DIR}/estimate_job.success"
