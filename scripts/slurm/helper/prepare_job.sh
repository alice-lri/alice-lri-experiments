#!/bin/bash
set -eo pipefail
pushd "$PROJECT_ROOT" > /dev/null

ACTUAL_DB_DIR="$1"
ARG_TYPE="$2"
REBUILD="$3"
BUILD_OPTIONS="$4"


if [[ "$REBUILD" == true ]]; then
  source scripts/common/build.sh "$BUILD_OPTIONS"

  echo "Building and installing Python package..."
  rm -Rf "${ALICE_LRI_PYTHON_SRC}/build"
  pip install "${ALICE_LRI_PYTHON_SRC}" --target "${ALICE_LRI_PIP_DIR}" --upgrade
fi

if [[ "$ARG_TYPE" != "intrinsics" ]]; then
  echo "Quick test..."
  export PYTHONPATH="$ALICE_LRI_PIP_DIR:$PYTHONPATH"
  python -u -m scripts.slurm.ri_compression.run_ri_experiment --mode test
fi

echo "Preparing job..."
cp "${BASE_DB_DIR}/initial.sqlite" "${ACTUAL_DB_DIR}/initial.sqlite"
python -m scripts.slurm.helper.insert_experiment_row "${ACTUAL_DB_DIR}/initial.sqlite" "$ARG_TYPE" --build-options "$BUILD_OPTIONS"

popd > /dev/null
