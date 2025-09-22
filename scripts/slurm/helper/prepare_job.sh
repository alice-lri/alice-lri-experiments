#!/bin/bash
set -eo pipefail
pushd "$(dirname "${BASH_SOURCE[0]}")" > /dev/null

ACTUAL_DB_DIR="$1"
ARG_TYPE="$2"
REBUILD="$3"
BUILD_OPTIONS="$4"


if [[ "$REBUILD" == true ]]; then
  source ../../common/build.sh "$BUILD_OPTIONS"
  pip install "${ACCURATE_RI_PYTHON_SRC}" --target "${ACCURATE_RI_PIP_DIR}" --upgrade
fi

if [[ "$ARG_TYPE" != "intrinsics" ]]; then
  echo "Quick test..."
  export PYTHONPATH="$ACCURATE_RI_PIP_DIR:$PYTHONPATH"
  python -u run_ri_experiment.py --mode test
fi

echo "Preparing job..."
cp "${BASE_DB_DIR}/initial.sqlite" "${ACTUAL_DB_DIR}/initial.sqlite"
python ../helper/insert_experiment_row.py "${ACTUAL_DB_DIR}/initial.sqlite" "$ARG_TYPE" --build-options "$BUILD_OPTIONS"

popd > /dev/null
