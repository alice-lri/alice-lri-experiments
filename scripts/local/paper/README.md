# Paper Metrics Generation Scripts

This folder contains scripts for generating all tables and figures reported in the ALICE-LRI paper from the experiment results stored in `master.sqlite`.

## Overview

The [`generate_paper_metrics.sh`](generate_paper_metrics.sh) script is the main entry point that runs all individual Python scripts in sequence to produce the complete set of paper outputs. All generated tables and figures are saved to `results/paper/` (with tables and other data in `results/paper/data/` and figures in `results/paper/figures/`).

LaTeX tables are typically saved as `.tex` files that can be directly included in a LaTeX document.

## Prerequisites
- `master.sqlite` database must be present at `results/db/master.sqlite` (see [`results/README.md`](../../../results/README.md) for how to obtain it)
- All dependencies installed via [`scripts/common/install.sh`](../../common/install.sh) TODO: specify which dependencies are needed

## Main Script

### `generate_paper_metrics.sh`

Executes all paper metric generation scripts.

**Usage:**
```bash
./generate_paper_metrics.sh
```


## Running Individual Scripts

To run a specific script, use Python module syntax from the project root:

```bash
python -m scripts.local.paper.helper.generate_ablation_table
python -m scripts.local.paper.helper.generate_alice_times_table
# etc.
```

Each script in the `helper/` subfolder generates specific tables or figures. You can run these individually if you only need to regenerate specific outputs:

### Algorithm Analysis

- **`generate_vote_for_discontinuities_data.py`**
  - Generates Hough voting accumulator comparison data.
  - Creates CSV files comparing regular vs continuous voting strategies.
  - Output: `hough_continuity_regular.csv` and `hough_continuity_continuous.csv`.

- **`generate_scanline_counts_table.py`**
  - Computes confusion matrix metrics for scanline count predictions.
  - Calculates precision, recall, F1 scores, and Overall Accuracy (OA).
  - Filters for "robust" samples (scanlines with point count ≥ 64).
  - Output: `scanline_count_metrics.tex`.

- **`generate_resolutions_table.py`**
  - Computes metrics for horizontal angular resolution predictions.
  - Calculates incorrect count and Overall Accuracy (OA).
  - Separates "all samples" vs "robust only" (n^(l) ≥ 64) subsets.
  - Output: `resolution_metrics.tex`.

### Intrinsics Estimation Results

- **`generate_per_beam_metrics_table.py`**
  - Computes per-beam intrinsic parameter estimation errors.
  - Calculates MAX (maximum error) and MAE (mean absolute error).
  - Separates "all frames" vs "robust_only" (point count ≥ 64) subsets.
  - Output: `per_beam_metrics.tex`.

- **`generate_ablation_table.py`**
  - Performs ablation study analysis for algorithm components.
  - Tests combinations: Hough Continuity, Conflict Resolution, Vertical Heuristics, Horizontal Heuristics.
  - Measures impact on incorrect scanline counts and incorrect resolutions.
  - Queries database for both KITTI and DurLAR datasets.
  - Output: `ablation_combined_metrics.tex`.

### Range Image Results

- **`generate_range_image_metrics_table.py`**
  - Computes range image reconstruction quality metrics.
  - Calculates Chamfer Distance (CD in meters), PSNR (dB), and Sampling Error (SE in %).
  - Compares PBEA vs ALICE methods at different resolutions.
  - Output: `range_image_comparison.tex` and per-frame CSV files in `cd_by_frame_csvs/` sub-folder.

- **`generate_range_image_qualitative.py`**
  - Generates qualitative visualizations of range image reconstructions.
  - Creates 3D point cloud reconstructions (original vs PBEA vs ALICE).
  - Generates range image visualizations comparing PBEA and ALICE.
  - Output: PNG files for 3D reconstructions and PDF files for range images.

### Runtime Analysis

- **`generate_alice_times_table.py`**
  - Measures ALICE-LRI runtime performance across datasets.
  - Reports estimation time (seconds), projection time (ms), unprojection time (ms).
  - Computes mean and standard deviation grouped by dataset.
  - Optionally runs `measure_times.cpp` executable if CSV doesn't exist.
  - Output: `runtime_performance.tex`.

- **`generate_rtst_times_table.py`**
  - Measures RTST encoding/decoding runtime performance.
  - Calculates overhead of modified vs original method.
  - Reports mean encoding/decoding times grouped by error threshold.
  - Optionally runs `measure_rtst_times.py` if CSV doesn't exist.
  - Output: `rtst_times.tex`.

### Compression Results

- **`generate_rtst_metrics_table_and_figure.py`**
  - Computes compression metrics using RTST.
  - Calculates Compression Ratio (CR), Chamfer Distance (CD), PSNR, Sampling Error (SE).
  - Compares original vs modified (ALICE) range images at different error thresholds.
  - Generates CR vs CD scatter plot data.
  - Output: `compression_comparison.tex`, `compression_original.csv`, `compression_ours.csv`.

## Notes

- **Runtime Benchmarks**: Scripts that measure runtime (`generate_alice_times_table.py`, `generate_rtst_times_table.py`) will skip benchmarking if the corresponding CSV files exist in `results/csv/`. Delete the CSV files to force re-running the benchmarks.
- **Reproducibility**: The generated outputs should match the tables and figures in the paper.
- **Output**: For more details on the output structure and generated files, see [`results/README.md`](../../../results/README.md).

---

For the complete workflow, see the main [REPRODUCIBILITY.md](../../../REPRODUCIBILITY.md).
