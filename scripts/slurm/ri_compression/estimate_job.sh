#!/bin/bash
#SBATCH -J alice_lri_application
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

echo "Beginning intrinsics estimation job..."

export PYTHONPATH="$ALICE_LRI_PIP_DIR:$PYTHONPATH"

pushd "$PROJECT_ROOT" > /dev/null
srun apptainer exec "$CONTAINER_PATH" \
 python -u -m scripts.slurm.ri_compression.run_ri_experiment --mode batch \
 --phase=estimate \
 --type="${ARG_TYPE}" \
 --db_path="${DB_DIR}/initial.sqlite" \
 --kitti_root="${KITTI_PATH}" \
 --durlar_root="${DURLAR_PATH}" \
 --private_dir="${TMPDIR}" \
 --shared_dir="${SHARED_DIR}"
popd > /dev/null

echo "Intrinsics estimation job finished."
touch "${DB_DIR}/estimate_job.success"
