#!/bin/bash
set -euo pipefail

CONTAINER_PATH="../../container.sif"
COMMAND="$*"

#TODO extract variable
CONDA_ENV_NAME="accurate_ri_env"
apptainer exec "$CONTAINER_PATH" bash -c "source /opt/conda/etc/profile.d/conda.sh && conda activate '$CONDA_ENV_NAME' && \"$COMMAND\""
