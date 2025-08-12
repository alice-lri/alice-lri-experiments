#!/bin/bash
set -eo pipefail

JOB_COUNT=32

BATCH_ID="$(date +'%Y%m%d_%H%M%S_%3N')"
RELAUNCH_BATCH=false
REBUILD=true
USER_REQUESTED_JOBS=()
JOBS_TO_RUN=()
BUILD_OPTIONS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --build-options)
      shift
      if [[ $# -eq 0 ]]; then
        echo "Error: --build-options requires at least one argument." >&2
        exit 1
      fi
      while [[ $# -gt 0 && "$1" != --* ]]; do
        BUILD_OPTIONS+=("$1")
        shift
      done
      ;;
    --relaunch)
      shift
      if [[ $# -eq 0 ]]; then
        echo "Error: --relaunch requires a batch ID." >&2
        exit 1
      fi
      BATCH_ID="$1"
      RELAUNCH_BATCH=true
      shift
      while [[ $# -gt 0 && "$1" != --* ]]; do
        if [[ "$1" =~ ^[0-9]+$ ]]; then
          USER_REQUESTED_JOBS+=("$1")
          shift
        else
          echo "Invalid job index: $1" >&2
          exit 1
        fi
      done
      ;;
    --skip-build)
      REBUILD=false
      shift
      ;;
    *)
      echo "Invalid arg: $1" >&2
      exit 1
      ;;
  esac
done

ACTUAL_LOGS_DIR="${BASE_LOGS_DIR}/${BATCH_ID}"
ACTUAL_DB_DIR="${BASE_DB_DIR}/${BATCH_ID}"
SHARED_DIR="${BASE_DB_DIR}/${BATCH_ID}/shared"

if [ "$RELAUNCH_BATCH" = true ]; then
  if [ ! -d "${ACTUAL_LOGS_DIR}" ]; then
    echo "Log directory ${ACTUAL_LOGS_DIR} does not exist."
    exit 1
  fi

  if [ ! -d "${ACTUAL_DB_DIR}" ]; then
    echo "DB directory ${ACTUAL_DB_DIR} does not exist."
    exit 1
  fi

  if [ "${#USER_REQUESTED_JOBS[@]}" -gt 0 ]; then
    JOBS_TO_RUN=("${USER_REQUESTED_JOBS[@]}")
  else
    for i in $(seq 0 $((JOB_COUNT - 1))); do
      if [ ! -f "${ACTUAL_DB_DIR}/job_${i}.success" ]; then
        JOBS_TO_RUN+=("$i")
      fi
    done
  fi
else
  if [ "${#USER_REQUESTED_JOBS[@]}" -gt 0 ]; then
    JOBS_TO_RUN=("${USER_REQUESTED_JOBS[@]}")
  else
    for i in $(seq 0 $((JOB_COUNT - 1))); do
      JOBS_TO_RUN+=("$i")
    done
  fi
fi

echo "Build options: ${BUILD_OPTIONS[*]}"
echo "Will run jobs: ${JOBS_TO_RUN[*]}"
read -r -p "Continue? (y/n): " CONTINUE

if [ "$CONTINUE" != "y" ]; then
  echo "Aborting."
  exit 1
fi

echo "Batch ID: ${BATCH_ID}"

mkdir -p "${ACTUAL_DB_DIR}"
mkdir -p "${ACTUAL_LOGS_DIR}"
mkdir -p "${SHARED_DIR}"
