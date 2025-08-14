#!/bin/bash
set -eo pipefail

pushd "$(dirname "${BASH_SOURCE[0]}")" > /dev/null

ACCURATE_RI_SRC="$(realpath ../accurate-ri)"
ACCURATE_RI_PYTHON_SRC="${ACCURATE_RI_SRC}/python"
RTST_SRC="$(realpath ../rtst/src)"
RTST_MODIFIED_SRC="$(realpath ../rtst-modified/src)"
BUILD_OPTIONS="$1"

echo "Fetching dependencies..."
conan install "${ACCURATE_RI_SRC}/lib" -s compiler.cppstd=gnu20 -s build_type=Release --output-folder="${ACCURATE_RI_SRC}/build/lib" --build=missing
conan install "${ACCURATE_RI_SRC}/examples" -s compiler.cppstd=gnu20 -s build_type=Release --output-folder="${ACCURATE_RI_SRC}/build/examples" --build=missing

echo "Building project..."
cmake -DCMAKE_BUILD_TYPE=Release -DLOG_LEVEL=NONE -DENABLE_TRACE_FILE=OFF -DENABLE_PROFILING=OFF -DLIB_MODE=ON $BUILD_OPTIONS -S "${ACCURATE_RI_SRC}" -B "${ACCURATE_RI_SRC}/build"
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

popd > /dev/null
