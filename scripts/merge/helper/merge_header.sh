#!/bin/bash
set -eo pipefail
pushd "$(dirname "${BASH_SOURCE[0]}")" > /dev/null

source ../../common/load_env.sh

TARGET_DIR=""
REMOVE_TARGET=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target-dir)
      shift
      if [[ $# -eq 0 ]]; then
        echo "Error: --target-dir requires a directory argument." >&2
        exit 1
      fi
      TARGET_DIR="$BASE_DB_DIR/$1"
      shift
      ;;
    --remove-target-dir)
      REMOVE_TARGET=true
      shift
      ;;
    *)
      echo "Invalid arg: $1" >&2
      exit 1
      ;;
  esac
done

if [ -z "$TARGET_DIR" ]; then
  TARGET_DIR=$(ls -td1 "${BASE_DB_DIR}"/*/ | head -1)
  echo "No target directory specified. Using latest: ${TARGET_DIR}"
  echo "Continue? (y/n)"
  read -r CONTINUE
  if [ "$CONTINUE" != "y" ]; then
    echo "Aborting."
    exit 1
  fi
fi


popd > /dev/null
