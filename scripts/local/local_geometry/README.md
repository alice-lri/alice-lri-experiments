# Local Geometry Experiment

This folder contains the local workstation runner for the experiment.
It computes symmetric local point-to-plane errors for ALICE-LRI and the PBEA
resolution sweep without writing to the main experiment database.

The core metric is implemented in:

- `scripts/common/helper/local_geometry_metrics.py`

Shared reconstruction/evaluation helpers used by both the local and SLURM
runners are implemented in:

- `scripts/common/helper/local_geometry_experiment.py`

The local runner writes derived outputs to `results/local_geometry/` by default:

- `local_geometry_metrics.csv`
- `local_geometry_metrics.sqlite`, table `local_geometry_frame_result`

## Quick Sanity Run

Run this script from the `alice_lri_env` conda environment. The Python bindings
for `alice_lri` are not available in the default system Python on the local
workstation.

```bash
/home/samuel.soutullo/.miniconda3/envs/alice_lri_env/bin/python \
  scripts/local/local_geometry/run_local_geometry_experiment.py \
  --max_frames_per_dataset 1 \
  --overwrite
```

By default the script uses `LOCAL_SQLITE_INITIAL_DB`, which is enough here
because the database is only used for frame selection. Any database passed with
`--db_path` is opened in SQLite read-only mode. The output SQLite file is a
derived result file under `results/local_geometry/`.

To bypass DB frame selection:

```bash
/home/samuel.soutullo/.miniconda3/envs/alice_lri_env/bin/python \
  scripts/local/local_geometry/run_local_geometry_experiment.py \
  --frame kitti:2011_09_30/2011_09_30_drive_0018_sync/velodyne_points/data/0000000000.bin \
  --overwrite
```

Use a larger local subset for the final local check:

```bash
/home/samuel.soutullo/.miniconda3/envs/alice_lri_env/bin/python \
  scripts/local/local_geometry/run_local_geometry_experiment.py \
  --max_frames_per_dataset 10 \
  --k_neighbors 12 \
  --overwrite
```

The runner always evaluates ALICE-LRI plus the same PBEA resolution sweep used
by the range-image reconstruction experiment. The native PBEA resolutions are
`4000 x 64` for KITTI and `2048 x 128` for DurLAR, followed by multipliers
`2, 4, 8, 16, 32` in each dimension. PBEA rows are stored as `pbea_native`,
`pbea_x2`, ..., `pbea_x32`.
