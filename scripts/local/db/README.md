# Database Schema Documentation

This folder contains scripts for creating and populating the experiment database. The database uses SQLite and stores dataset metadata, ground truth information, and experiment results.

## Overview

The database schema is designed to support:
1. **Dataset and Frame Management**: References to KITTI and DurLAR datasets and their individual frames.
2. **Ground Truth Data**: Per-sensor reference intrinsic parameters and per-frame laser-scanline mappings.
3. **Experiment Results**: Results from intrinsics estimation, range image, and compression experiments.

## Entity-Relationship Diagram

```plantuml
@startuml
!define table(x) class x << (T,#FFAAAA) >>
!define primary_key(x) <u>x</u>
!define foreign_key(x) <i>x</i>

hide methods
hide stereotypes

' Dataset and Frame entities
table(dataset) {
  primary_key(id): INTEGER
  name: TEXT
  laser_count: INTEGER
  max_range: REAL
}

table(dataset_frame) {
  primary_key(id): INTEGER
  foreign_key(dataset_id): INTEGER
  relative_path: TEXT
}

table(dataset_laser_gt) {
  primary_key(id): INTEGER
  foreign_key(dataset_id): INTEGER
  laser_idx: INTEGER
  vertical_offset: REAL
  vertical_angle: REAL
  horizontal_offset: REAL
  horizontal_resolution: INTEGER
  horizontal_angle_offset: REAL
}

table(dataset_frame_gt) {
  primary_key(id): INTEGER
  foreign_key(dataset_frame_id): INTEGER
  points_count: INTEGER
  scanlines_count: INTEGER
}

table(dataset_frame_scanline_gt) {
  primary_key(id): INTEGER
  foreign_key(dataset_frame_id): INTEGER
  foreign_key(laser_id): INTEGER
  scanline_idx: INTEGER
  points_count: INTEGER
}

' Intrinsics experiment entities
table(intrinsics_experiment) {
  primary_key(id): INTEGER
  timestamp: TEXT
  label: TEXT
  description: TEXT
  commit_hash: TEXT
  use_hough_continuity: BOOLEAN
  use_scanline_conflict_solver: BOOLEAN
  use_vertical_heuristics: BOOLEAN
  use_horizontal_heuristics: BOOLEAN
}

table(intrinsics_frame_result) {
  primary_key(id): INTEGER
  foreign_key(experiment_id): INTEGER
  foreign_key(dataset_frame_id): INTEGER
  points_count: INTEGER
  scanlines_count: INTEGER
  vertical_iterations: INTEGER
  unassigned_points: INTEGER
  end_reason: TEXT
}

table(intrinsics_scanline_result) {
  primary_key(id): INTEGER
  foreign_key(intrinsics_result_id): INTEGER
  scanline_idx: INTEGER
  points_count: INTEGER
  vertical_offset: REAL
  vertical_angle: REAL
  ... (CI and uncertainty fields)
  horizontal_offset: REAL
  horizontal_resolution: INTEGER
  horizontal_angle_offset: REAL
}

' Range Image experiment entities
table(ri_experiment) {
  primary_key(id): INTEGER
  timestamp: TEXT
  label: TEXT
  description: TEXT
  commit_hash: TEXT
}

table(ri_frame_result) {
  primary_key(id): INTEGER
  foreign_key(experiment_id): INTEGER
  foreign_key(dataset_frame_id): INTEGER
  method: TEXT
  ri_width: INTEGER
  ri_height: INTEGER
  original_points_count: REAL
  reconstructed_points_count: REAL
  ... (MSE and RMSE metrics)
}

' Compression experiment entities
table(compression_experiment) {
  primary_key(id): INTEGER
  timestamp: TEXT
  label: TEXT
  description: TEXT
  commit_hash: TEXT
}

table(compression_frame_result) {
  primary_key(id): INTEGER
  foreign_key(experiment_id): INTEGER
  foreign_key(dataset_frame_id): INTEGER
  horizontal_step: REAL
  vertical_step: REAL
  tile_size: INTEGER
  error_threshold: REAL
  ... (compression metrics)
}

' Relationships
dataset "1" -- "N" dataset_frame
dataset "1" -- "N" dataset_laser_gt
dataset_frame "1" -- "1" dataset_frame_gt
dataset_frame "1" -- "N" dataset_frame_scanline_gt
dataset_laser_gt "1" -- "N" dataset_frame_scanline_gt

intrinsics_experiment "1" -- "N" intrinsics_frame_result
dataset_frame "1" -- "N" intrinsics_frame_result
intrinsics_frame_result "1" -- "N" intrinsics_scanline_result

ri_experiment "1" -- "N" ri_frame_result
dataset_frame "1" -- "N" ri_frame_result

compression_experiment "1" -- "N" compression_frame_result
dataset_frame "1" -- "N" compression_frame_result

@enduml
```

## Schema Details

### Core Dataset Tables

- **`dataset`**: Stores dataset metadata (KITTI, DurLAR).
- **`dataset_frame`**: Individual frames within each dataset, referenced by relative path.
- **`dataset_laser_gt`**: Per-sensor reference intrinsic parameters for each laser, fixed per dataset.
- **`dataset_frame_gt`**: Summary statistics for each frame's ground truth.
- **`dataset_frame_scanline_gt`**: Per-frame laser-scanline mappings, linking active scanlines to their corresponding lasers.

### Experiment Tables

Each experiment type (intrinsics, range image, compression) follows a similar pattern:

1. **Experiment Metadata Table** (e.g., `intrinsics_experiment`): Stores experiment configuration, timestamp, label, and description.
2. **Frame Results Table** (e.g., `intrinsics_frame_result`): Stores per-frame results for the experiment.
3. **Detailed Results Table** (e.g., `intrinsics_scanline_result`): Stores detailed per-scanline results for intrinsics experiments.

## Ground Truth Philosophy

The ground truth system implements a two-level approach to ensure fair and consistent evaluation:

### Level 1: Per-Sensor Reference Parameters (`dataset_laser_gt`)
- Contains fixed intrinsic parameters for each laser in a sensor, derived from manufacturer specifications and calibration data.
- Parameters include: elevation angles, vertical offsets, horizontal offsets, horizontal resolutions, and angular offsets.
- These values remain **constant across all frames** of a dataset to ensure consistent evaluation.

### Level 2: Per-Frame Laser-Scanline Mappings (`dataset_frame_scanline_gt`)
- Maps which predefined scanlines are present in each specific frame.
- Since not all laser beams always yield returns, the number of active scanlines $L$ may vary between frames.
- For each frame, this table records which lasers produced returns and maps them to their corresponding scanline indices.
- The intrinsic parameters themselves (from `dataset_laser_gt`) remain unchanged; only the presence/absence of scanlines varies.

This two-level design allows ALICE-LRI to be evaluated against consistent reference parameters while accounting for the practical reality that some laser beams may not return data in every frame.

## Usage

### Creating the Initial Database

Run [`create_initial_db.sh`](create_initial_db.sh) to generate the `initial.sqlite` database:

```bash
./create_initial_db.sh
```

This will:
1. Create the database schema from [`helper/experiments_db.sql`](helper/experiments_db.sql).
2. Scan the KITTI and DurLAR datasets (paths from `.env`).
3. Populate `dataset`, `dataset_frame`, and `dataset_laser_gt` tables with metadata and reference parameters.


To understand the overall workflow, see the main [REPRODUCIBILITY.md](../../../REPRODUCIBILITY.md).
