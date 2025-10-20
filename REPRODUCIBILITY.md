# Reproducibility Guide

This guide explains how to fully reproduce the experiments, results, and figures for the ALICE-LRI paper. It covers dataset setup, environment configuration, experiment execution, and result generation, referencing the relevant scripts and READMEs throughout.

## Prerequisites

### Local Dependencies

To analyze the experiments locally, ensure the following are installed on your workstation:

- **C++20** compatible compiler with CMake >= 3.20
- **Python** (>= 3.8)
- **pip**
- **Conan** (>= 2.0, can be installed via `pip install conan`)
	- First time using Conan? Run `conan profile detect` after installing to create a default profile.
- **SQLite3 CLI** (can be installed via `apt install sqlite3` on Ubuntu/Debian)
- **Apptainer** (optional; only needed if you want to build the HPC container image yourself—otherwise, you can download the pre-built image as detailed below) 

### HPC Dependencies

On the HPC cluster, you need:

- A Linux environment with **SLURM** for job scheduling
- **Apptainer** (or Singularity) for container execution

## 1. Download Required Datasets


You will need the full KITTI (raw) and DurLAR datasets, both on your local workstation and on the HPC cluster.

- **KITTI (raw):** Download from [KITTI Raw Data](https://www.cvlibs.net/datasets/kitti/raw_data.php). You can use the official download script provided on that page.
- **DurLAR:** Download from [DurLAR GitHub](https://github.com/l1997i/DurLAR).

**Tip:** To avoid downloading twice, it is recommended to download the datasets directly on the HPC cluster and then mount the dataset folders on your local workstation using `sshfs` or a similar tool.

## 2. Clone the Repository

Clone this repository on both your local workstation and your HPC system:

```bash
git clone --recurse-submodules https://github.com/alice-lri/alice-lri-experiments.git
cd alice-lri-experiments
```

This will automatically clone the repository along with its submodules (`alice-lri` and `rtst-modified`).

The following steps will specify where each action should be performed (local workstation or HPC).

## 3. Update the `.env` File

**Location: Both local and HPC**

Edit the [`.env`](.env) file to set the correct paths for both environments. Make sure the following variables point to the correct locations:

- `LOCAL_KITTI_PATH`, `LOCAL_DURLAR_PATH` (for your workstation)
- `KITTI_PATH`, `DURLAR_PATH` (for the HPC cluster)
- `ALICE_LRI_HPC_MODULES` (modules to load on HPC)

Refer to the comments in [`.env`](.env) for more details.

## 4. Build and Install the Project

**Location: Local workstation**

After configuring your `.env` file locally, build and install the project dependencies and binaries:

1. **Install Python dependencies:**
   ```bash
   pip install -r scripts/local/requirements.txt
   ```

2. **Build and install the project:**
   ```bash
   scripts/common/install.sh
   ```

This will install all required Python packages (numpy, pandas, matplotlib, scikit-learn, python-dotenv) and build the ALICE-LRI C++ library with Python bindings.

## 5. Obtain the `initial.sqlite` Database

**Location: Local workstation, then transfer to HPC**

You need the `initial.sqlite` database, which contains references to all dataset frames and metadata, including per-sensor reference intrinsic parameters (elevation angles, spatial and azimuthal offsets, and horizontal resolutions) derived from manufacturer specifications and sensor calibration data. There are two ways to get it (see also [`results/README.md`](results/README.md)):

- **Option 1: Generate Locally**
	
	Run the database creation script after downloading the datasets:
	```bash
	scripts/local/db/create_initial_db.sh
	```
	Then copy the resulting file to the HPC cluster (e.g., using `scp`) at `${BASE_DB_DIR}/initial.sqlite` (where `BASE_DB_DIR` is specified in your `.env` file).

- **Option 2: Download Pre-built**
	- Download from [https://nextcloud.citius.gal/s/alice_lri_initial_db](https://nextcloud.citius.gal/s/alice_lri_initial_db).
	- Place it locally in `results/db/initial.sqlite` and copy to the HPC at `${BASE_DB_DIR}/initial.sqlite`.

## 6. Obtain the Container Image

**Location: Local workstation (build), then transfer to HPC; or download directly on HPC**

The project uses a container for reproducible environments on the HPC. See [`container/README.md`](container/README.md) for details. In summary:

- **Option 1: Build Locally and Transfer**
	
	Build the container inside the `container/` folder on your local workstation (requires Apptainer/Singularity):
	```bash
	cd container
	apptainer build container.sif container.def
	```
	
	Then transfer the resulting `container.sif` to the HPC cluster at `<repo>/container/container.sif`.

- **Option 2: Download Directly on HPC**
	- Download from [https://nextcloud.citius.gal/s/alice_lri_container](https://nextcloud.citius.gal/s/alice_lri_container) directly on the HPC and place it in the [`container/`](container/) folder.

## 7. Reproducing Paper Experiments

**Location: HPC cluster**

### Overview

After preparing the environment and datasets, you can run the main experiments on the HPC cluster. The workflow consists of:

1. **Running experiments**: For each experiment type, navigate to the corresponding [`scripts/slurm/`](scripts/slurm/) subfolder and run the `prepare_and_launch.sh` script. These scripts submit jobs to the SLURM scheduler and manage experiment execution. See [`scripts/slurm/README.md`](scripts/slurm/README.md) for details on command-line options.

2. **Merging results**: After each experiment (or set of experiments), merge the results into the master database using [`scripts/merge/merge_db.sh`](scripts/merge/merge_db.sh). This script can be run on a login or interactive compute node. You can merge after each experiment or after all are complete, but **do not run multiple merges in parallel**. Each merge updates or creates the `master.sqlite` database in your `BASE_DB_DIR`. For detailed information on merge options and workflow, see [`scripts/merge/README.md`](scripts/merge/README.md).

3. **Transferring results**: Once all experiments are merged, copy the final `master.sqlite` to your local machine for analysis:
   ```bash
   scp <your_hpc_user>@<hpc_address>:${BASE_DB_DIR}/master.sqlite results/db/master.sqlite
   ```

**Alternative:** You can skip all previous steps and download the pre-built `master.sqlite` database directly from [https://nextcloud.citius.gal/s/alice_lri_master_db](https://nextcloud.citius.gal/s/alice_lri_master_db) as described in [`results/README.md`](results/README.md).

### Experiment Execution

To fully reproduce all experiments exactly as reported in the paper, follow these specific steps. Each experiment involves running a `prepare_and_launch.sh` script followed by merging the results with `scripts/merge/merge_db.sh`.

#### 7.1. Ground Truth Experiment

Compute per-frame ground truth laser-scanline assignments. Since the number of scanlines may vary between frames (some laser beams may not yield returns), this experiment verifies which predefined scanlines are present in each frame and maps them to their corresponding lasers. The intrinsic parameters themselves remain fixed per dataset to ensure fair evaluation.

For details on the two-level ground truth approach (per-sensor reference parameters vs. per-frame laser-scanline mappings), see [`scripts/local/db/README.md`](scripts/local/db/README.md#ground-truth-philosophy).

```bash
cd scripts/slurm/ground_truth
./prepare_and_launch.sh
```

After completion, merge the results:

```bash
cd scripts/merge
./merge_db.sh
# Select: [4] Ground Truth
```

#### 7.2. Intrinsics Experiments (Including Ablation Study)

Run the intrinsics experiments with different algorithm configurations.

**Important**: Remember to merge the results after each intrinsics experiment completes.

Each command below represents a different ablation:

**Default (all components enabled):**
```bash
cd ../slurm/intrinsics
./prepare_and_launch.sh --build-options \
  -DFLAG_USE_HOUGH_CONTINUITY=ON \
  -DFLAG_USE_SCANLINE_CONFLICT_SOLVER=ON \
  -DFLAG_USE_VERTICAL_HEURISTICS=ON \
  -DFLAG_USE_HORIZONTAL_HEURISTICS=ON
```

**Without Hough continuity:**
```bash
./prepare_and_launch.sh --build-options \
  -DFLAG_USE_HOUGH_CONTINUITY=OFF \
  -DFLAG_USE_SCANLINE_CONFLICT_SOLVER=ON \
  -DFLAG_USE_VERTICAL_HEURISTICS=ON \
  -DFLAG_USE_HORIZONTAL_HEURISTICS=ON
```

**Without scanline conflict solver:**
```bash
./prepare_and_launch.sh --build-options \
  -DFLAG_USE_HOUGH_CONTINUITY=ON \
  -DFLAG_USE_SCANLINE_CONFLICT_SOLVER=OFF \
  -DFLAG_USE_VERTICAL_HEURISTICS=ON \
  -DFLAG_USE_HORIZONTAL_HEURISTICS=ON
```

**Without vertical heuristics:**
```bash
./prepare_and_launch.sh --build-options \
  -DFLAG_USE_HOUGH_CONTINUITY=ON \
  -DFLAG_USE_SCANLINE_CONFLICT_SOLVER=ON \
  -DFLAG_USE_VERTICAL_HEURISTICS=OFF \
  -DFLAG_USE_HORIZONTAL_HEURISTICS=ON
```

**Without horizontal heuristics:**
```bash
./prepare_and_launch.sh --build-options \
  -DFLAG_USE_HOUGH_CONTINUITY=ON \
  -DFLAG_USE_SCANLINE_CONFLICT_SOLVER=ON \
  -DFLAG_USE_VERTICAL_HEURISTICS=ON \
  -DFLAG_USE_HORIZONTAL_HEURISTICS=OFF
```

**Without conflict solver and continuity:**
```bash
./prepare_and_launch.sh --build-options \
  -DFLAG_USE_HOUGH_CONTINUITY=OFF \
  -DFLAG_USE_SCANLINE_CONFLICT_SOLVER=OFF \
  -DFLAG_USE_VERTICAL_HEURISTICS=ON \
  -DFLAG_USE_HORIZONTAL_HEURISTICS=ON
```

**Without any heuristics:**
```bash
./prepare_and_launch.sh --build-options \
  -DFLAG_USE_HOUGH_CONTINUITY=ON \
  -DFLAG_USE_SCANLINE_CONFLICT_SOLVER=ON \
  -DFLAG_USE_VERTICAL_HEURISTICS=OFF \
  -DFLAG_USE_HORIZONTAL_HEURISTICS=OFF
```

**Minimal (all enhancements disabled):**
```bash
./prepare_and_launch.sh --build-options \
  -DFLAG_USE_HOUGH_CONTINUITY=OFF \
  -DFLAG_USE_SCANLINE_CONFLICT_SOLVER=OFF \
  -DFLAG_USE_VERTICAL_HEURISTICS=OFF \
  -DFLAG_USE_HORIZONTAL_HEURISTICS=OFF
```

After each intrinsics experiment completes, merge the results (once per experiment):

```bash
cd scripts/merge
./merge_db.sh
# Select: [1] Intrinsics
# Provide your desired label and description for each experiment
# Example:
# - label: intrinsics_default
# - description: Intrinsics experiment with all components enabled.
```

#### 7.3. Range Image Experiment

Run the range image experiment with all components enabled:

```bash
cd ../slurm/ri_compression
./prepare_and_launch.sh --build-options \
  -DFLAG_USE_HOUGH_CONTINUITY=ON \
  -DFLAG_USE_SCANLINE_CONFLICT_SOLVER=ON \
  -DFLAG_USE_VERTICAL_HEURISTICS=ON \
  -DFLAG_USE_HORIZONTAL_HEURISTICS=ON
# Select: [1] Range Image
```

After completion, merge the results:

```bash
cd scripts/merge
./merge_db.sh
# Select: [2] Range Image
# Provide your desired label and description for the experiment
# Example:
# - label: ri_final_default
# - description: Final RI experiment with all the parts of the algorithm enabled.
```

#### 7.4. Compression Experiment

Run the compression experiment with all components enabled:

```bash
cd ../slurm/ri_compression
./prepare_and_launch.sh --build-options \
  -DFLAG_USE_HOUGH_CONTINUITY=ON \
  -DFLAG_USE_SCANLINE_CONFLICT_SOLVER=ON \
  -DFLAG_USE_VERTICAL_HEURISTICS=ON \
  -DFLAG_USE_HORIZONTAL_HEURISTICS=ON
# Select: [2] Compression
```

After completion, merge the results:

```bash
cd scripts/merge
./merge_db.sh
# Select: [3] Compression
# Provide your desired label and description for the experiment
# Example:
# - label: compression_final_default
# - description: Final compression experiment with all the parts of the algorithm enabled.
```

## 8. Generate Tables and Figures

**Location: Local workstation**

After all experiments are complete and merged, ensure you have copied the final [`master.sqlite`](results/db/master.sqlite) from the HPC to your local machine as explained in **Step 8**. 

This step will aggregate results from the `master.sqlite` database and perform runtime analysis on your local workstation. The runtime analysis includes:
- **ALICE-LRI runtime analysis**: Generates the runtime table for the ALICE-LRI algorithm (stored in `results/csv/alice_times.csv`).
- **RTST compression comparison**: Generates the runtime performance comparison between the original and modified RTST compression algorithm (stored in `results/csv/rtst_times.csv`).

By default, the runtime analysis is **not re-run** if the CSV files already exist. If the CSV files are missing, you will be prompted to confirm whether you want to run the runtime benchmarks.

In summary, to generate all tables and figures for the paper, run:

```bash
scripts/local/paper/generate_paper_metrics.sh
```

This will produce all outputs as described in [`results/README.md`](results/README.md).

**Note:** Each set of tables and figures is generated separately by individual Python scripts within `generate_paper_metrics.sh`. You can run these scripts individually if you only need to regenerate specific outputs. For details on each script and what it generates, see [`scripts/local/paper/README.md`](scripts/local/paper/README.md).

---

For more details on any step, see the relevant README files in each folder.
