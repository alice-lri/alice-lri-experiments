#!/bin/bash
set -eo pipefail

BASE_DB_DIR="$1"
ACTUAL_DB_DIR="$2"

source ../../local/build.sh
source ../helper/paths.sh

pip install "${ACCURATE_RI_PYTHON_SRC}" --target "${ACCURATE_RI_PIP_DIR}" --upgrade

echo "Quick test..."
export PYTHONPATH="$ACCURATE_RI_PIP_DIR:$PYTHONPATH"
python run_compression_experiment.py --mode test

echo "Preparing job..."
cp "${BASE_DB_DIR}/initial.sqlite" "${ACTUAL_DB_DIR}/initial.sqlite"
python ../helper/insert_experiment_row.py "${ACTUAL_DB_DIR}/initial.sqlite" compression
