# Local Scripts

This folder contains scripts designed to run on your **local workstation** (as opposed to the HPC cluster). These scripts handle database setup, result analysis, and paper metrics generation.

## Overview

The local scripts are organized into three main categories:

### 1. **`db/`** - Database Setup and Schema

Contains scripts for creating and managing the SQLite databases used throughout the project.

- **`create_initial_db.sh`**: Creates the `initial.sqlite` database with dataset metadata and ground truth intrinsic parameters
- **Database schema documentation**: Complete documentation of all database tables and relationships

See [`db/README.md`](db/README.md) for detailed information about the database schema, ground truth philosophy, and how to create the initial database.

### 2. **`paper/`** - Paper Metrics Generation

Contains scripts for generating all tables and figures reported in the ALICE-LRI paper from the experiment results.

- **`generate_paper_metrics.sh`**: Main script that runs all paper generation scripts in sequence
- **`helper/`**: Individual Python scripts that generate specific tables or figures

See [`paper/README.md`](paper/README.md) for detailed documentation on each script and what outputs it produces.

### 3. **`runtime/`** - Runtime Benchmarking

Contains scripts for measuring runtime performance:

- **`measure_rtst_times.py`**: Measures encoding/decoding times for the RTST compression codec

These scripts are invoked automatically by the paper generation scripts when needed, but can also be run independently.

## Prerequisites

Before running any local scripts, ensure you have:

1. **Python 3.8+** installed
2. **Dependencies installed** via [`scripts/common/install.sh`](../common/install.sh) TODO: specify which dependencies are needed
3. **Datasets downloaded** (KITTI and DurLAR) as described in [`REPRODUCIBILITY.md`](../../REPRODUCIBILITY.md)
4. **Environment configured** via [`.env`](../../.env) file

## Workflow

For the complete workflow, see [`REPRODUCIBILITY.md`](../../REPRODUCIBILITY.md).
