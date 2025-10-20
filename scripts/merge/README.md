# Database Merge Scripts

This folder contains scripts for merging experiment databases from HPC jobs into the master database. After running experiments on the HPC cluster, these scripts consolidate all individual job results into a single `master.sqlite` database for analysis.

## Overview

When experiments run on the HPC, each SLURM job writes results to its own partial database file. The merge scripts combine these partial databases into the master database while preserving data integrity and avoiding duplicates.

### Important Notes

- **Run on HPC**: These scripts are designed to run **on the HPC cluster** (login or interactive compute node), not on your local workstation. After merging, you can transfer the `master.sqlite` file to your local machine for analysis.
- **Sequential Execution**: Do not run multiple merge operations in parallel.
- **Multiple Experiments**: You can merge multiple experiments sequentially into the same `master.sqlite` database. Each experiment (e.g., ablation studies with different configurations) will be stored as a separate entry with its own label and description, allowing for comparative analysis across all experiments.
- **Backups**: Backups are created automatically for the `master.sqlite` file before merging. They will be named as `master.sqlite.bak`, `master.sqlite.bak.1`, etc.

## Main Script: `merge_db.sh`

The main entry point for merging experiment results.

### Usage

```bash
./merge_db.sh [OPTIONS]
```

The script will:
1. Prompt you to select the experiment type to merge
2. Automatically detect the latest results directory (or use the one you specify)
3. Ask for experiment metadata (label and description) if applicable
4. Create a backup of the current `master.sqlite` before merging
5. Merge all partial databases into `master.sqlite`

### Interactive Prompts

When you run `merge_db.sh`, you'll be prompted to select the experiment type:

```
Select experiment type:
[1] Intrinsics
[2] Range Image
[3] Compression
[4] Ground Truth
Enter choice:
```

For experiment types 1-3, you'll also be asked for:
- **Experiment label**: A short identifier (e.g., `intrinsics_default`, `ablation_no_hough`)
- **Experiment description**: A detailed description of the experiment configuration

For ground truth experiments, no label or description is needed.

### Command-Line Options

The script accepts the following options (defined in [`helper/merge_header.sh`](helper/merge_header.sh)):

- `--target-dir <dirname>`
  
  Specify which results directory to merge from within `$BASE_DB_DIR`. The directory name should be relative to `BASE_DB_DIR`.
  
  If not specified, the script will automatically select the most recently modified directory in `$BASE_DB_DIR` and ask for confirmation.
  
  Example:
  ```bash
  ./merge_db.sh --target-dir 20250115_143022_572
  ```

- `--remove-target-dir`
  
  Automatically remove the target directory after successful merging. Use this to clean up partial databases once they've been merged.
  
  Example:
  ```bash
  ./merge_db.sh --remove-target-dir
  ```

You can combine options:
```bash
./merge_db.sh --target-dir 20250115_143022_intrinsics_001 --remove-target-dir
```

## Workflow

For the complete workflow, see [`REPRODUCIBILITY.md`](../../REPRODUCIBILITY.md).
