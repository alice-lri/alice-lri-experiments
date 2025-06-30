#!/bin/bash
set -eo pipefail

pushd "$(dirname "$0")" > /dev/null

source build.sh
pip install "${ACCURATE_RI_PYTHON_SRC}" --upgrade

popd > /dev/null
