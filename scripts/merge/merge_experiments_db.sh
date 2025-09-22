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

module load $ALICE_LRI_HPC_MODULES
apptainer exec "$CONTAINER_PATH" \
  python helper/merge_db.py "$TARGET_DIR" "$BASE_DB_DIR/master.sqlite" \
  --type="${ARG_TYPE}" \
  --label="$LABEL" \
  --description="$DESCRIPTION"

echo "Experiments database merged successfully."

popd > /dev/null
