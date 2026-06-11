#!/bin/bash
set -eo pipefail

DB_DIR=$1
SHARED_DIR=$2

if [ -z "$3" ] || [ -z "$4" ]; then
  TASK_INDEX=$SLURM_PROCID
  TASK_COUNT=$SLURM_NTASKS
else
  JOB_INDEX=$3
  JOB_COUNT=$4
  TASK_INDEX=$(( JOB_INDEX * SLURM_NTASKS + SLURM_PROCID ))
  TASK_COUNT=$(( JOB_COUNT * SLURM_NTASKS ))
fi

./task_item.sh "$DB_DIR" "$SHARED_DIR" "$TASK_INDEX" "$TASK_COUNT"
