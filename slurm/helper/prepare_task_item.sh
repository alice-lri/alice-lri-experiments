#!/bin/bash
set -eo pipefail

DB_FILE_PATH="${DB_DIR}/${TASK_INDEX}.sqlite"
SUCCESS_FILE_PATH="${DB_DIR}/task_${TASK_INDEX}.success"
TRACE_FOLDER_PATH="${DB_DIR}/traces"
TRACE_FILE_PATH="${TRACE_FOLDER_PATH}/${TASK_INDEX}.log"

rm -f "${DB_FILE_PATH}"
rm -f "${SUCCESS_FILE_PATH}"
rm -f "${TRACE_FILE_PATH}"

cp "${DB_DIR}/initial.sqlite" "${DB_FILE_PATH}"

mkdir -p "${TRACE_FOLDER_PATH}"
