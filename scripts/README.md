# Scripts Overview

This folder contains all scripts for running the ALICE-LRI experiments, from database setup through experiment execution to paper figure generation. Scripts are organized by their intended execution environment (HPC cluster vs local workstation) and purpose.

## Folder Structure

### **slurm/** - HPC Experiment Execution

Scripts for running experiments on the HPC cluster using SLURM job scheduling. These scripts handle:
- Ground truth computation (per-frame laser-scanline assignments)
- Intrinsics estimation experiments (including ablation studies)
- Range image reconstruction experiments
- Compression experiments

Each experiment type has a `prepare_and_launch.sh` script that submits jobs to SLURM and manages parallelization across 32 jobs (64 cores each by default).

**See [`slurm/README.md`](slurm/README.md)** for detailed usage instructions, command-line options, and parallelization configuration.

### **merge/** - Database Merging (HPC)

Scripts for merging partial experiment databases from HPC jobs into the master database. After experiments complete, these scripts:
- Consolidate individual job results into `master.sqlite`
- Handle multiple experiment types (intrinsics, range image, compression, ground truth)
- Support sequential merging of multiple experiments for comparative analysis
- Create automatic backups before each merge

**See [`merge/README.md`](merge/README.md)** for merge workflow, command-line options, and how to manage multiple experiments.

### **local/** - Local Workstation Scripts

Scripts for database setup and result analysis on your local workstation. Includes:
- **db/**: Database creation and schema management
  - Creates `initial.sqlite` with dataset metadata and ground truth parameters
  - Database schema documentation with E-R diagrams
- **paper/**: Paper metrics generation
  - Generates all tables and figures from `master.sqlite`
  - Individual scripts for each paper output
- **runtime/**: Runtime benchmarking utilities

**See [`local/README.md`](local/README.md)** for overview of local scripts organization.  
**See [`local/db/README.md`](local/db/README.md)** for database schema and ground truth philosophy.  
**See [`local/paper/README.md`](local/paper/README.md)** for detailed documentation of each paper generation script.

### **common/** - Shared Utilities

General-purpose scripts and modules used across both local and HPC environments:
- **build.sh**, **install.sh**: Build and dependency installation scripts
- **load_env.py**, **load_env.sh**: Environment variable loading from `.env` file
- **helper/**: Shared Python modules for data handling, database operations, and utilities

### **cpp/** - C++ Utilities

C++ programs for specific computational tasks:
- Runtime measurement utilities
- Database interaction tools
- Performance benchmarking programs

## Workflow

For the complete workflow from database setup to paper figure generation, see the main [`REPRODUCIBILITY.md`](../REPRODUCIBILITY.md) document.