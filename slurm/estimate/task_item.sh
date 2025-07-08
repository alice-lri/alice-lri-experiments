#!/bin/bash
set -eo pipefail

EXECUTABLE_PATH=$1
DB_DIR=$2
TASK_INDEX=$3
TASK_COUNT=$4

EXEC_DIR=$(dirname "$EXECUTABLE_PATH")
EXEC_FILE=$(basename "$EXECUTABLE_PATH")

cd "$EXEC_DIR" || { echo "Failed to cd into $EXEC_DIR"; exit 1; }

source ../helper/prepare_task_item.sh

echo "Running task $TASK_INDEX of $TASK_COUNT..."
./"$EXEC_FILE" "$TASK_INDEX" "$TASK_COUNT" 2>&1 | tee "${TRACE_FILE_PATH}"

touch "${SUCCESS_FILE_PATH}"