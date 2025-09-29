#!/bin/bash
set -eo pipefail
pushd "$(dirname "${BASH_SOURCE[0]}")" > /dev/null

source ../common/load_env.sh

BUILD_OPTIONS="$1"

echo "Fetching dependencies..."
conan install "${ALICE_LRI_LIB_SRC}" -s compiler.cppstd=gnu20 -s build_type=Release --output-folder="${ALICE_LRI_LIB_PATH}" --build=missing
conan install "${CPP_SCRIPTS_SRC}" -s compiler.cppstd=gnu20 -s build_type=Release --output-folder="${CPP_SCRIPTS_SRC}/build" --build=missing

echo "Building ALICE-LRI..."
cmake -DCMAKE_BUILD_TYPE=Release -DLOG_LEVEL=NONE -DENABLE_TRACE_FILE=OFF -DENABLE_PROFILING=OFF $BUILD_OPTIONS -S "${ALICE_LRI_LIB_SRC}" -B "${ALICE_LRI_LIB_PATH}"
make -C "${ALICE_LRI_LIB_PATH}"

echo "Building C++ scripts..."
cmake -DCMAKE_BUILD_TYPE=Release -S "${CPP_SCRIPTS_SRC}" -B "${CPP_SCRIPTS_SRC}/build"
make -C "${CPP_SCRIPTS_SRC}/build"

echo "Building modified RTST"
make -C "$RTST_MODIFIED_SRC"

popd > /dev/null
