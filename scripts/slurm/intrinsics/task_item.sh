#!/bin/bash
set -eo pipefail

DB_DIR=$1
TASK_INDEX=$2
TASK_COUNT=$3

EXEC_DIR=$(dirname "$INTRINSICS_SQL_EXECUTABLE_PATH")
EXEC_FILE=$(basename "$INTRINSICS_SQL_EXECUTABLE_PATH")

source ../helper/prepare_task_item.sh

cd "$EXEC_DIR" || { echo "Failed to cd into $EXEC_DIR"; exit 1; }

echo "Running task $TASK_INDEX of $TASK_COUNT..."
./"$EXEC_FILE" "$TASK_INDEX" "$TASK_COUNT" 2>&1 | tee "${TRACE_FILE_PATH}" || { echo "Failed task: $TASK_INDEX"; exit 1; }

touch "${SUCCESS_FILE_PATH}"
