#!/bin/bash
set -eo pipefail

CONDA_ENV_NAME="$1"
BASE_DB_DIR="$2"
ACTUAL_DB_DIR="$3"

ACCURATE_RI_SRC="../../accurate-ri"
ACCURATE_RI_PYTHON_SRC="${ACCURATE_RI_SRC}/python"
RTST_SRC="../../rtst/src"
RTST_MODIFIED_SRC="../../rtst-modified/src"

source ../../conda/init_conda.sh
source /opt/conda/etc/profile.d/conda.sh
conda activate "$CONDA_ENV_NAME"

echo "Fetching dependencies..."
conan install ${ACCURATE_RI_SRC}/lib -s compiler.cppstd=gnu20 -s build_type=Release --output-folder="${ACCURATE_RI_SRC}/build/lib" --build=missing
conan install ${ACCURATE_RI_SRC}/examples -s compiler.cppstd=gnu20 -s build_type=Release --output-folder="${ACCURATE_RI_SRC}/build/examples" --build=missing

echo "Building project..."
cmake -DCMAKE_BUILD_TYPE=Release -DLOG_LEVEL=NONE -DENABLE_TRACE_FILE=OFF -DENABLE_PROFILING=OFF -DLIB_MODE=ON -S "${ACCURATE_RI_SRC}" -B "${ACCURATE_RI_SRC}/build"
make -C "${ACCURATE_RI_SRC}/build"

echo "Building original RTST"
make -C "$RTST_SRC"

echo "Building modified RTST"
make -C "$RTST_MODIFIED_SRC"

echo "Building Python library..."
rm -Rf "${ACCURATE_RI_PYTHON_SRC}/build"
conan install "${ACCURATE_RI_SRC}/lib" -s compiler.cppstd=gnu20 -s build_type=Release -of "${ACCURATE_RI_PYTHON_SRC}/build/lib" --build=missing
cmake -DCMAKE_BUILD_TYPE=Release -DLOG_LEVEL=NONE -DENABLE_TRACE_FILE=OFF -DENABLE_PROFILING=OFF -DLIB_MODE=ON -S "${ACCURATE_RI_PYTHON_SRC}" -B "${ACCURATE_RI_PYTHON_SRC}/build" -G Ninja
ninja -C "${ACCURATE_RI_PYTHON_SRC}/build"
pip install -e "${ACCURATE_RI_PYTHON_SRC}"

echo "Quick test..."
python run_compression_experiment.py --mode test

echo "Preparing job..."
cp "${BASE_DB_DIR}/initial.sqlite" "${ACTUAL_DB_DIR}/initial.sqlite"
python ../helper/insert_experiment_row.py "${ACTUAL_DB_DIR}/initial.sqlite" compression
