#!/bin/bash
set -eo pipefail

BASE_DB_DIR="$1"
ACTUAL_DB_DIR="$2"
ARG_TYPE="$3"
REBUILD=$4
BUILD_OPTIONS="$5"


source ../helper/paths.sh

if [[ "$REBUILD" == true ]]; then
  source ../../local/build.sh "$BUILD_OPTIONS"
  pip install "${ACCURATE_RI_PYTHON_SRC}" --target "${ACCURATE_RI_PIP_DIR}" --upgrade
fi

if [[ "$ARG_TYPE" != "intrinsics" ]]; then
  echo "Quick test..."
  export PYTHONPATH="$ACCURATE_RI_PIP_DIR:$PYTHONPATH"
  python -u python/run_ri_experiment.py --mode test
fi

echo "Preparing job..."
cp "${BASE_DB_DIR}/initial.sqlite" "${ACTUAL_DB_DIR}/initial.sqlite"
python ../helper/insert_experiment_row.py "${ACTUAL_DB_DIR}/initial.sqlite" "$ARG_TYPE"
