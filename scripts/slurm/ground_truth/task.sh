#!/bin/bash
set -eo pipefail

DB_DIR=$1

if [ -z "$2" ] || [ -z "$3" ]; then
  TASK_INDEX=$SLURM_PROCID
  TASK_COUNT=$SLURM_NTASKS
else
  JOB_INDEX=$2
  JOB_COUNT=$3
  TASK_INDEX=$(( JOB_INDEX * SLURM_NTASKS + SLURM_PROCID ))
  TASK_COUNT=$(( JOB_COUNT * SLURM_NTASKS ))
fi

./task_item.sh "$DB_DIR" "$TASK_INDEX" "$TASK_COUNT"
