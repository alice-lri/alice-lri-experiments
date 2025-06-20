#!/bin/bash
set -eo pipefail
cd "$(dirname "$0")" || exit

#source ../helper/paths.sh
#source ../helper/multi_batch_job_header.sh

ACCURATE_RI_SRC="../../accurate-ri"
RTST_SRC="../../rtst/src"
RTST_MODIFIED_SRC="../../rtst-modified/src"

echo "Fetching dependencies..."
conan install ${ACCURATE_RI_SRC}/lib -s compiler.cppstd=gnu20 -s build_type=Release --output-folder="${ACCURATE_RI_SRC}/build/lib" --build=missing
conan install ${ACCURATE_RI_SRC}/examples -s compiler.cppstd=gnu20 -s build_type=Release --output-folder="${ACCURATE_RI_SRC}/build/examples" --build=missing

echo "Building project..."
cmake -DCMAKE_BUILD_TYPE=Release -DLOG_LEVEL=NONE -DENABLE_TRACE_FILE=OFF -DENABLE_PROFILING=OFF -DLIB_MODE=ON -S "${ACCURATE_RI_SRC}" -B "${ACCURATE_RI_SRC}/build"
make -C "${ACCURATE_RI_SRC}/build"

echo "Building original RTST"
#make -C "$RTST_SRC"

echo "Building modified RTST"
make -C "$RTST_MODIFIED_SRC"

exit 1
source ../../conda/init_conda.sh

echo "Preparing job..."
cp "${BASE_DB_DIR}/initial.sqlite" "${ACTUAL_DB_DIR}/initial.sqlite"
python pre_job.py "${ACTUAL_DB_DIR}/initial.sqlite"

jq -n \
  --arg db_dir "$ACTUAL_DB_DIR" \
  --arg durlar "$DURLAR_PATH" \
  --arg kitti "$KITTI_PATH" \
  '{
    db_dir: $db_dir,
    dataset_root_path: {
      durlar: $durlar,
      kitti: $kitti
    }
  }' > "${SRC_PATH}/build/examples/config.json"


for i in "${JOBS_TO_RUN[@]}"; do
  echo "Launching job ${i}..."
  sbatch --job-name="accurate_ri_${i}" -o "${ACTUAL_LOGS_DIR}/${i}.log" -e "${ACTUAL_LOGS_DIR}/${i}.log" \
   job.sh "${CONDA_ENV_NAME}" "${SRC_PATH}/build/examples/${EXECUTABLE_NAME}" "${ACTUAL_DB_DIR}" \
    "${i}" "${JOB_COUNT}"
done