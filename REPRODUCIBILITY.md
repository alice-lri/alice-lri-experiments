# Reproducibility Guide

This guide explains how to fully reproduce the experiments, results, and figures for this project. It covers dataset setup, environment configuration, experiment execution, and result generation, referencing the relevant scripts and READMEs throughout.

## Prerequisites

### Local Dependencies

To analyze the experiments locally, ensure the following are installed on your workstation:

- **g++** (C++ compiler)
- **CMake**
- **Python**
- **pip**
- **Conan** (>= 2.0, can be installed via `pip install conan`)
- **Apptainer** (optional; only needed if you want to build the HPC container image yourself—otherwise, you can download the pre-built image as detailed below)

### HPC Dependencies

On the HPC cluster, you need:

- A Linux environment with **SLURM** for job scheduling
- **Apptainer** (or Singularity) for container execution

**Note:** You must edit the [`.env`](.env) file to specify the correct module(s) to load on your HPC system using the `ALICE_LRI_HPC_MODULES` variable. This ensures the environment is set up correctly for experiment execution. Refer to the comments in [`.env`](.env) for more details on configuring paths and modules.

## 1. Download Required Datasets


You will need the full KITTI (raw) and DurLAR datasets, both on your local workstation and on the HPC cluster.

- **KITTI (raw):** Download from [KITTI Raw Data](https://www.cvlibs.net/datasets/kitti/raw_data.php). You can use the official download script provided on that page.
- **DurLAR:** Download from [DurLAR GitHub](https://github.com/l1997i/DurLAR).

**Tip:** To avoid downloading twice, it is recommended to download the datasets directly on the HPC cluster and then mount the dataset folders on your local workstation using `sshfs` or a similar tool.

## 2. Update the `.env` File

Edit the [`/.env`](.env) file to set the correct paths for both your local and HPC environments. Make sure the following variables point to the correct locations:

- `LOCAL_KITTI_PATH`, `LOCAL_DURLAR_PATH` (for your workstation)
- `KITTI_PATH`, `DURLAR_PATH` (for the HPC cluster)

Refer to the comments in [`.env`](.env) for more details.

## 3. Build and Install the Project

After configuring your `.env` file, build and install the project dependencies and binaries by running [`scripts/common/install.sh`](scripts/common/install.sh). This script will set up the required environment for both local and HPC usage.

## 4. Obtain the `initial.sqlite` Database


You need the `initial.sqlite` database, which contains references to all dataset frames and metadata. There are two ways to get it (see also [`results/README.md`](results/README.md)):

- **Option 1: Generate Locally**
	- Run [`scripts/local/db/create_initial_db.sh`](scripts/local/db/create_initial_db.sh) after downloading the datasets. This will scan the datasets and create [`results/db/initial.sqlite`](results/db/initial.sqlite).
	- Copy the resulting file to the HPC cluster at the path specified by `BASE_DB_DIR` in your `.env` (e.g., using `scp`).
- **Option 2: Download Pre-built**
	- Download from [https://nextcloud.citius.gal/s/alice_lri_initial_db](https://nextcloud.citius.gal/s/alice_lri_initial_db) and place it in the correct location on both your local and HPC systems.

## 5. Obtain the Container Image


The project uses a container for reproducible environments. See [`container/README.md`](container/README.md) for details. In summary:

- **Option 1: Build Locally**
	- Run `apptainer build container.sif container.def` inside the [`container/`](container/) folder (requires Apptainer/Singularity).
	- Transfer the resulting [`container/container.sif`](container/container.sif) to the HPC cluster.
- **Option 2: Download Pre-built**
	- Download from [https://nextcloud.citius.gal/s/alice_lri_container](https://nextcloud.citius.gal/s/alice_lri_container) and place it in the [`container/`](container/) folder on the HPC.

## 6. Clone the Repository and Configure

- Clone this repository on your HPC system.
- Update the `.env` file on the HPC to match the correct dataset and storage paths.

## 7. Run Experiments on the HPC


After preparing the environment and datasets, you can run the main experiments. For each experiment type, navigate to the corresponding [`scripts/slurm/`](scripts/slurm/) subfolder and run the `prepare_and_launch.sh` script:

- [`scripts/slurm/ground_truth/prepare_and_launch.sh`](scripts/slurm/ground_truth/prepare_and_launch.sh)
- [`scripts/slurm/intrinsics/prepare_and_launch.sh`](scripts/slurm/intrinsics/prepare_and_launch.sh)
- [`scripts/slurm/ri_compression/prepare_and_launch.sh`](scripts/slurm/ri_compression/prepare_and_launch.sh)

These scripts will submit jobs to the SLURM scheduler and manage experiment execution.

## 8. Merge Experiment Results


After each experiment (or set of experiments), you must merge the results into the master database. Use the merge script on the HPC (can be run on a login or interactive compute node):

- [`scripts/merge/merge_db.sh`](scripts/merge/merge_db.sh)

You can merge after each experiment or after all are complete, but **do not run multiple merges in parallel**. Each merge updates or creates the [`master.sqlite`](results/db/master.sqlite) database in your `BASE_DB_DIR`.

Once all experiments are merged, copy the final [`master.sqlite`](results/db/master.sqlite) to your local machine for analysis (e.g., using `scp`).


**Alternative:** You can skip all previous steps and download the pre-built [`master.sqlite`](results/db/master.sqlite) database directly from [https://nextcloud.citius.gal/s/alice_lri_master_db](https://nextcloud.citius.gal/s/alice_lri_master_db) as described in [`results/README.md`](results/README.md).

## 9. Generate Tables and Figures


To generate all tables and figures for the paper, run:

```bash
scripts/local/paper/generate_paper_metrics.sh
```

or simply execute [`scripts/local/paper/generate_paper_metrics.sh`](scripts/local/paper/generate_paper_metrics.sh).

This will produce all outputs as described in [`results/README.md`](results/README.md).

---

For more details on any step, see the relevant README files in each folder.
