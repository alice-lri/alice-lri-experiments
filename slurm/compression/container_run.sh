#!/bin/bash
set -euo pipefail

CONTAINER_PATH="../../container.sif"

source ../../conda/init_conda.sh
apptainer exec "$CONTAINER_PATH" bash -c "source /opt/conda/etc/profile.d/conda.sh && conda activate '$CONDA_ENV_NAME' && exec \"$@\""
