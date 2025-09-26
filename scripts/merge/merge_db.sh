#!/bin/bash
set -eo pipefail
pushd "$(dirname "${BASH_SOURCE[0]}")" > /dev/null

source helper/merge_header.sh

echo "Select experiment type:"
echo "[1] Intrinsics"
echo "[2] Range Image"
echo "[3] Compression"
echo "[4] Ground Truth"
read -r -p "Enter choice: " EXPERIMENT_TYPE

if [[ "$EXPERIMENT_TYPE" == "1" ]]; then
  ARG_TYPE="experiments"
elif [[ "$EXPERIMENT_TYPE" == "2" ]]; then
  ARG_TYPE="ri_experiments"
elif [[ "$EXPERIMENT_TYPE" == "3" ]]; then
  ARG_TYPE="compression_experiments"
elif [[ "$EXPERIMENT_TYPE" == "4" ]]; then
  ARG_TYPE="ground_truth"
else
  echo "Invalid choice."
  exit 1
fi

echo "Will use arg type: ${ARG_TYPE}"

if [[ "$ARG_TYPE" == "ground_truth" ]]; then
  echo "Merging ground truth databases from ${TARGET_DIR}..."
else
  read -rp "Experiment label: " LABEL
  read -rp "Experiment description: " DESCRIPTION

  echo "Merging experiments databases from ${TARGET_DIR}..."
fi

MASTER_DB="${BASE_DB_DIR}/master.sqlite"
if [[ ! -f "$MASTER_DB" ]]; then
  echo "Master database not found at ${MASTER_DB}. Copying initial database to master."
  cp "${BASE_DB_DIR}/initial.sqlite" "$MASTER_DB"
fi

module load $ALICE_LRI_HPC_MODULES

pushd "$PROJECT_ROOT" > /dev/null
apptainer exec "$CONTAINER_PATH" \
  python -m scripts.merge.helper.merge_db "$TARGET_DIR" "$MASTER_DB" \
  --type="${ARG_TYPE}" \
  --label="$LABEL" \
  --description="$DESCRIPTION"
popd > /dev/null

echo "Experiments database merged successfully."

if [[ "$REMOVE_TARGET" == true ]]; then
  echo "Removing target directory ${TARGET_DIR}..."
  rm -rf "$TARGET_DIR"
  echo "Target directory removed."
fi

popd > /dev/null
