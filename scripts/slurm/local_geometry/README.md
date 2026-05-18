# Local Geometry SLURM Experiment

This folder launches the local point-to-plane geometry experiment on the
HPC cluster. It follows the same partial-database pattern as the other SLURM
experiments: each task copies `initial.sqlite`, writes a task-local SQLite file,
and the merge scripts later consolidate all numbered `*.sqlite` files.

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
```

The runner evaluates both methods:

- `alice_lri`
- `pbea_native`

with `k_neighbors = 12`, KITTI PBEA at `4000 x 64`, and DurLAR PBEA at
`2048 x 128`.

## Merge

After the jobs finish, merge through the standard merge entry point:

```bash
cd ../../merge
./merge_db.sh --target-dir <BATCH_ID>
```

Select option `[5] Local Geometry`, then provide an experiment label and
description.
