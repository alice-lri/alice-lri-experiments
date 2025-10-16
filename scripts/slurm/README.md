# SLURM Scripts README

This folder contains all scripts and helpers for running experiments on the HPC cluster using SLURM. The scripts are organized by experiment type, and each subfolder provides the necessary job scripts and launchers for a specific set of experiments.

## Structure

- **ground_truth/**: Scripts for ground truth database generation and related experiments.
- **intrinsics/**: Scripts for running intrinsics estimation experiments.
- **ri_compression/**: Scripts for range image and compression experiments.
- **helper/**: Shared helper scripts and utilities used by the main experiment scripts.

## Main Usage: `prepare_and_launch.sh`

Each experiment type has a `prepare_and_launch.sh` script in its subfolder. This is the main entry point for launching experiments on the cluster. These scripts:

- Prepare the required environment and input files (e.g., copy databases, set up configs).
- Submit the appropriate SLURM jobs for the experiment type, using the corresponding `job.sh` and `task.sh` scripts.
- Manage job dependencies and logging.

TODO: Explain better what each is done for, and the ground truth flow.

### How to Use

1. **Navigate to the desired experiment subfolder:**
  - `ground_truth/`, `intrinsics/`, or `ri_compression/`
2. **Run the entry point script:**
  ```bash
  ./prepare_and_launch.sh [OPTIONS]
  ```
  You may be prompted for experiment options or parameters, depending on the script.
3. **Monitor job progress:**
  - Logs are written to the specified logs directory (see your `.env` configuration).
  - SLURM job status can be checked with `squeue` or similar commands.

#### Parallelization and Resource Usage

Each `prepare_and_launch.sh` script invokes `sbatch` to submit multiple jobs to the SLURM scheduler, each using the corresponding `job.sh` script. By default, these launch **32 separate jobs**, each requesting **64 cores**. This configuration was chosen to optimize resource usage and queue times: instead of one large, demanding job, the workload is split into many smaller jobs (each processing a subset of dataset frames), which tend to start sooner and make better use of available resources.

The parallelization is done on a per-dataset-frame basis, so jobs do not need to run simultaneously. If you wish to adjust the number of jobs or the resources requested per job, you can:

- Change the `JOB_COUNT` variable in [`helper/multi_batch_job_header.sh`](helper/multi_batch_job_header.sh) to set how many jobs are launched.
- Edit the `#SBATCH` parameters in the corresponding `job.sh` file in each experiment subfolder to change the number of cores or other SLURM options.

In theory, you can adjust these settings as needed; all dataset frames will still be processed and distributed as evenly as possible. However, only the provided configuration has been empirically tested.

#### Command-Line Options

All `prepare_and_launch.sh` scripts support the following options (see [`helper/multi_batch_job_header.sh`](helper/multi_batch_job_header.sh)):

- `--build-options <flag1> [flag2 ...]`
  
  Pass one or more CMake build flags directly to CMake. These control algorithm components for the ablation study (mainly used with the `intrinsics/prepare_and_launch.sh`). The allowed flags are:
  - `-DFLAG_USE_HOUGH_CONTINUITY=ON|OFF`
  - `-DFLAG_USE_SCANLINE_CONFLICT_SOLVER=ON|OFF`
  - `-DFLAG_USE_VERTICAL_HEURISTICS=ON|OFF`
  - `-DFLAG_USE_HORIZONTAL_HEURISTICS=ON|OFF`
  
  By default, if not specified, all four flags are set to `ON`. To reproduce the ablation study, you can turn these flags on or off as needed. Example usage:
  
  ```bash
  ./prepare_and_launch.sh --build-options -DFLAG_USE_HOUGH_CONTINUITY=ON -DFLAG_USE_SCANLINE_CONFLICT_SOLVER=OFF
  ```

- `--relaunch <BATCH_ID> [job_idx ...]`
  
  Relaunch a previous batch by its ID, optionally specifying which job indices to rerun.
- `--skip-build`
  
  Skip the build step (useful if everything is already built).
- `--skip-estimation`
  
  Skip the estimation step (for experiment types that support it).

You can combine these options as needed. For example:

```bash
./prepare_and_launch.sh --build-options -DFLAG_USE_HOUGH_CONTINUITY=ON -DFLAG_USE_SCANLINE_CONFLICT_SOLVER=ON
./prepare_and_launch.sh --relaunch 20250101_120000_001 0 1 2
```

You will always be prompted to confirm before jobs are launched.

### Subfolder Details

- **ground_truth/**
  - `prepare_and_launch.sh`: Prepares and launches ground truth jobs.
  - `job.sh`, `task.sh`, `task_item.sh`: SLURM job scripts for processing batches.
  - `populate_ground_truth_db.py`: Script for populating the ground truth database.

- **intrinsics/**
  - `prepare_and_launch.sh`: Prepares and launches intrinsics estimation jobs.
  - `job.sh`, `task.sh`, `task_item.sh`: SLURM job scripts for processing batches.

- **ri_compression/**
  - `prepare_and_launch.sh`: Prepares and launches range image and compression jobs. Prompts for experiment type (RI or compression).
  - `estimate_job.sh`: For running estimation jobs as a dependency.
  - `job.sh`, `task.sh`, `task_item.sh`: SLURM job scripts for processing batches.
  - `run_ri_experiment.py`: Python script for running RI experiments.

- **helper/**
  - `multi_batch_job_header.sh`, `prepare_job.sh`, `prepare_task_item.sh`: Shared shell helpers for job setup and management.
  - `insert_experiment_row.py`: Utility for database row insertion.

## Notes

- Always ensure your `.env` file is correctly configured for paths and environment variables before launching experiments.
- The `prepare_and_launch.sh` scripts are designed to be run from a login or interactive compute node on the HPC.
- For merging results after experiments, see the `merge/` folder and the main reproducibility guide.

For more details on experiment workflow and result handling, refer to the main [`REPRODUCIBILITY.md`](../../REPRODUCIBILITY.md).
