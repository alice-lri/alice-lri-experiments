#!/bin/bash
set -eo pipefail

pushd "$(dirname "${BASH_SOURCE[0]}")" > /dev/null

BUILD_OPTIONS="$1"

echo "Fetching dependencies..."
conan install "${ALICE_LRI_SRC}/lib" -s compiler.cppstd=gnu20 -s build_type=Release --output-folder="${ALICE_LRI_SRC}/build/lib" --build=missing
conan install "${ALICE_LRI_SRC}/examples" -s compiler.cppstd=gnu20 -s build_type=Release --output-folder="${ALICE_LRI_SRC}/build/examples" --build=missing

echo "Building project..."
cmake -DCMAKE_BUILD_TYPE=Release -DLOG_LEVEL=NONE -DENABLE_TRACE_FILE=OFF -DENABLE_PROFILING=OFF $BUILD_OPTIONS -S "${ALICE_LRI_SRC}" -B "${ALICE_LRI_SRC}/build"
make -C "${ALICE_LRI_SRC}/build"

echo "Building original RTST"
make -C "$RTST_SRC"

echo "Building modified RTST"
make -C "$RTST_MODIFIED_SRC"

echo "Building Python library..."
rm -Rf "${ALICE_LRI_PYTHON_SRC}/build"
conan install "${ALICE_LRI_SRC}/lib" -s compiler.cppstd=gnu20 -s build_type=Release -of "${ALICE_LRI_PYTHON_SRC}/build/lib" --build=missing
cmake -DCMAKE_BUILD_TYPE=Release -DLOG_LEVEL=NONE -DENABLE_TRACE_FILE=OFF -DENABLE_PROFILING=OFF -S "${ALICE_LRI_PYTHON_SRC}" -B "${ALICE_LRI_PYTHON_SRC}/build" -G Ninja
ninja -C "${ALICE_LRI_PYTHON_SRC}/build"

popd > /dev/null
