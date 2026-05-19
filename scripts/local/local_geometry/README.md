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

## Earlier Native-Only Validation

A one-frame-per-dataset run completed successfully with `alice_lri_env` before
the runner was switched to always execute the full PBEA sweep.
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

## Earlier n=100 Native-Only Subset

The first 100 frames per dataset also completed successfully before the runner
was switched to always execute the full PBEA sweep:

```bash
/usr/bin/time -v /home/samuel.soutullo/.miniconda3/envs/alice_lri_env/bin/python \
  -m scripts.local.local_geometry.run_local_geometry_experiment \
  --max_frames_per_dataset 100 \
  --k_neighbors 12 \
  --output_csv results/local_geometry/local_geometry_metrics_n100.csv \
  --output_sqlite results/local_geometry/local_geometry_metrics_n100.sqlite
```

The native-only run produced 400 rows and took 11:16.25 wall-clock seconds with
maximum RSS 729876 KB. Mean per-frame symmetric point-to-plane metrics:

| Dataset | Method | Mean | RMSE | Median | P95 | Max |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| DurLAR | ALICE-LRI | 7.876325e-07 | 0.000002 | 1.546443e-07 | 0.000003 | 0.000069 |
| DurLAR | PBEA native | 1.297986e-02 | 0.021774 | 8.606889e-03 | 0.037986 | 3.063795 |
| KITTI | ALICE-LRI | 2.017872e-04 | 0.000247 | 1.775679e-04 | 0.000465 | 0.000839 |
| KITTI | PBEA native | 1.578356e-02 | 0.035308 | 9.564307e-03 | 0.048665 | 3.986054 |

For full-dataset/HPC execution, prefer writing results per frame or per batch
instead of only at the end of the process.
