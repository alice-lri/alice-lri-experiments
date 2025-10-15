# Scripts Folder README

# Scripts Folder README

This folder contains scripts and helpers for building, running, and managing experiments in the project. Scripts are organized by their intended execution environment and purpose:

- **slurm/**: Scripts to be executed on the HPC cluster. These are the main experiment scripts and job definitions for large-scale or distributed runs. They automate experiment submission, data processing, and results collection using SLURM.

- **local/**: Scripts to be executed locally on your machine. Use these for database setup, experiment management, and generating tables or figures from results. This includes scripts for creating and populating the initial database, managing experiment definitions, and producing paper-ready tables and figures from experiment outputs.

- **common/**: General-purpose scripts and helpers used across both local and HPC environments. Includes build scripts, environment setup, and shared Python modules for data handling and processing.

- **cpp/**: C++ utilities. Contains C++ code to measure times, store results in databases, etc.

- **merge/**: Utilities for merging databases and experiment results, including scripts for combining SQLite databases and related helpers.

For detailed instructions on how to use these scripts and reproduce experiments, please refer to [REPRODUCIBILITY.md](../REPRODUCIBILITY.md) in the project root.
