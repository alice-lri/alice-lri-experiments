# Local Geometry Experiment

This folder contains the local workstation runner for the R2.7 revision experiment.
It computes symmetric local point-to-plane errors for ALICE-LRI and native-resolution
PBEA without writing to the main experiment database.

The core metric is implemented in:

- `scripts/common/helper/local_geometry_metrics.py`

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
  --methods pbea_native \
  --overwrite
```

Use both methods for the final local check:

```bash
/home/samuel.soutullo/.miniconda3/envs/alice_lri_env/bin/python \
  scripts/local/local_geometry/run_local_geometry_experiment.py \
  --max_frames_per_dataset 10 \
  --methods alice_lri pbea_native \
  --k_neighbors 12 \
  --overwrite
```

The native PBEA resolutions are fixed to `4000 x 64` for KITTI and `2048 x 128`
for DurLAR.

## First Local Validation

A one-frame-per-dataset run completed successfully with `alice_lri_env`.
Aggregate symmetric point-to-plane metrics:

| Dataset | Method | Mean | P95 |
| --- | --- | ---: | ---: |
| DurLAR | ALICE-LRI | 6.674746e-07 | 0.000003 |
| DurLAR | PBEA native | 1.369338e-02 | 0.040438 |
| KITTI | ALICE-LRI | 2.045530e-04 | 0.000466 |
| KITTI | PBEA native | 1.668872e-02 | 0.051642 |

This is a smoke test only, not the final paper result. It confirms that the
metric and reconstruction paths behave sensibly before running larger local or
CESGA batches.
