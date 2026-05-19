# Local Geometry SLURM Experiment

This folder launches the local point-to-plane geometry experiment on the
HPC cluster. It follows the same partial-database pattern as the other SLURM
experiments: each task copies `initial.sqlite`, writes a task-local SQLite file,
and the merge scripts later consolidate all numbered `*.sqlite` files.

Like `ri_compression`, this experiment uses a separate single-task intrinsics
estimation job. That job writes one JSON file per sequence into the batch
`shared/` directory, and all evaluation jobs read those files. Evaluation tasks
also keep a per-process in-memory cache, so each task only reads each needed
sequence intrinsics once. No evaluation task writes intrinsics files.

The runner shares reconstruction and per-frame evaluation logic with the local
debug runner through `scripts/common/helper/local_geometry_experiment.py`. The
point-to-plane metric itself lives in
`scripts/common/helper/local_geometry_metrics.py`.

## Schema Migration

The local-geometry tables are not created automatically by the launch flow.
Before launching, apply the migration to the HPC initial database:

```bash
sqlite3 "$BASE_DB_DIR/initial.sqlite" < scripts/local/db/sql/001_local_geometry_experiment.sql
```

If `"$BASE_DB_DIR/master.sqlite"` already exists before merging, apply the same
migration to it too:

```bash
sqlite3 "$BASE_DB_DIR/master.sqlite" < scripts/local/db/sql/001_local_geometry_experiment.sql
```

## Launch

From this folder on the HPC:

```bash
./prepare_and_launch.sh
```

Useful inherited options:

```bash
./prepare_and_launch.sh --skip-build
./prepare_and_launch.sh --relaunch <BATCH_ID> [job_idx ...]
./prepare_and_launch.sh --skip-estimation
```

The runner always evaluates ALICE-LRI plus the same PBEA resolution sweep used
by the range-image reconstruction experiment:

- `alice_lri`
- `pbea_native`
- `pbea_x2`
- `pbea_x4`
- `pbea_x8`
- `pbea_x16`
- `pbea_x32`

The native PBEA resolutions are `4000 x 64` for KITTI and `2048 x 128` for
DurLAR, and the `pbea_x*` rows multiply both dimensions by the indicated factor.
The method labels keep the existing `local_geometry_frame_result` uniqueness
constraint valid, so no schema migration is required for the sweep.

## Merge

After the jobs finish, merge through the standard merge entry point:

```bash
cd ../../merge
./merge_db.sh --target-dir <BATCH_ID>
```

Select option `[5] Local Geometry`, then provide an experiment label and
description.

When generating the paper table, the local paper helper includes all
method/resolution rows stored in the latest `local_geometry_base` experiment.
