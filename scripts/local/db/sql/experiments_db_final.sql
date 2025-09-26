CREATE TABLE dataset
(
    id integer PRIMARY KEY AUTOINCREMENT,
    name text NOT NULL UNIQUE,
    laser_count integer NOT NULL
);
CREATE INDEX dataset_name_idx ON dataset (name);

CREATE TABLE dataset_frame
(
    id integer PRIMARY KEY AUTOINCREMENT,
    dataset_id integer NOT NULL REFERENCES dataset (id),
    relative_path text NOT NULL UNIQUE
);
CREATE INDEX dataset_frame_dataset_id_idx ON dataset_frame (dataset_id);
CREATE INDEX dataset_frame_relative_path_idx ON dataset_frame (relative_path);

CREATE TABLE dataset_laser_gt
(
    id integer PRIMARY KEY AUTOINCREMENT,
    dataset_id integer NOT NULL REFERENCES dataset (id),
    laser_idx integer NOT NULL,
    vertical_offset real NOT NULL,
    vertical_angle real NOT NULL,
    horizontal_offset real NOT NULL,
    horizontal_resolution integer NOT NULL,
    horizontal_angle_offset real NOT NULL,
    UNIQUE (dataset_id, laser_idx)
);
CREATE INDEX dataset_laser_gt_dataset_id_idx ON dataset_laser_gt (dataset_id);

CREATE TABLE dataset_frame_gt
(
    id integer PRIMARY KEY AUTOINCREMENT,
    dataset_frame_id integer NOT NULL UNIQUE REFERENCES dataset_frame (id),
    points_count integer NOT NULL,
    scanlines_count integer NOT NULL
);
CREATE INDEX dataset_frame_gt_dataset_frame_id_idx ON dataset_frame_gt (dataset_frame_id);

CREATE TABLE dataset_frame_scanline_gt
(
    id integer PRIMARY KEY AUTOINCREMENT,
    dataset_frame_id integer NOT NULL REFERENCES dataset_frame (id),
    laser_id integer NOT NULL REFERENCES dataset_laser_gt (id),
    scanline_idx integer NOT NULL,

    UNIQUE (dataset_frame_id, laser_id),
    UNIQUE (dataset_frame_id, scanline_idx)
);
CREATE INDEX dataset_frame_scanline_gt_dataset_frame_id_idx ON dataset_frame_scanline_gt (dataset_frame_id);
CREATE INDEX dataset_frame_scanline_gt_dataset_frame_id_scanline_idx ON dataset_frame_scanline_gt (dataset_frame_id, laser_id);

CREATE TABLE intrinsics_experiment
(
    id integer PRIMARY KEY AUTOINCREMENT,
    timestamp text NOT NULL,
    label text,
    description text,
    commit_hash text,
    use_hough_continuity boolean NOT NULL,
    use_scanline_conflict_solver boolean NOT NULL,
    use_vertical_heuristics boolean NOT NULL,
    use_horizontal_heuristics boolean NOT NULL
);

CREATE TABLE intrinsics_frame_result
(
    id integer PRIMARY KEY AUTOINCREMENT NOT NULL,
    experiment_id integer NOT NULL REFERENCES intrinsics_experiment (id),
    dataset_frame_id integer NOT NULL REFERENCES dataset_frame (id),
    points_count integer NOT NULL,
    scanlines_count integer NOT NULL,
    vertical_iterations integer NOT NULL,
    unassigned_points integer NOT NULL,
    end_reason text CHECK ( end_reason IN ('ALL_ASSIGNED', 'MAX_ITERATIONS', 'NO_MORE_PEAKS') ) NOT NULL,

    UNIQUE (experiment_id, dataset_frame_id)
);
CREATE INDEX intrinsics_frame_result_experiment_id_idx ON intrinsics_frame_result (experiment_id);
CREATE INDEX intrinsics_frame_result_experiment_id_dataset_frame_id_idx ON intrinsics_frame_result (experiment_id, dataset_frame_id);

CREATE TABLE intrinsics_scanline_result
(
    id integer PRIMARY KEY AUTOINCREMENT,
    intrinsics_result_id integer NOT NULL REFERENCES intrinsics_frame_result (id),
    scanline_idx integer NOT NULL,
    points_count integer NOT NULL,
    vertical_offset real NOT NULL,
    vertical_angle real NOT NULL,
    vertical_ci_offset_lower real NOT NULL,
    vertical_ci_offset_upper real NOT NULL,
    vertical_ci_angle_lower real NOT NULL,
    vertical_ci_angle_upper real NOT NULL,
    vertical_theoretical_angle_bottom_lower real NOT NULL,
    vertical_theoretical_angle_bottom_upper real NOT NULL,
    vertical_theoretical_angle_top_lower real NOT NULL,
    vertical_theoretical_angle_top_upper real NOT NULL,
    vertical_uncertainty real NOT NULL,
    vertical_last_scanline boolean NOT NULL,
    vertical_hough_votes real NOT NULL,
    vertical_hough_hash text NOT NULL,
    horizontal_offset real NOT NULL,
    horizontal_resolution integer NOT NULL,
    horizontal_heuristic boolean NOT NULL,
    horizontal_angle_offset real NOT NULL,

    UNIQUE (intrinsics_result_id, scanline_idx)
);
CREATE INDEX intrinsics_scanline_result_intrinsics_result_id_idx ON intrinsics_scanline_result (intrinsics_result_id);
CREATE INDEX intrinsics_scanline_result_intrinsics_result_id_scanline_idx_idx ON intrinsics_scanline_result (intrinsics_result_id, scanline_idx);

CREATE TABLE compression_experiment
(
    id integer PRIMARY KEY AUTOINCREMENT,
    timestamp text NOT NULL,
    label text NOT NULL,
    description text NOT NULL,
    commit_hash text NULL
);

CREATE TABLE compression_frame_result
(
    id integer PRIMARY KEY AUTOINCREMENT NOT NULL,
    experiment_id integer NOT NULL REFERENCES compression_experiment (id),
    dataset_frame_id integer NOT NULL REFERENCES dataset_frame (id),
    horizontal_step real NOT NULL,
    vertical_step real NOT NULL,
    tile_size integer NOT NULL,
    error_threshold real NOT NULL,
    original_points_count integer NOT NULL,
    naive_points_count integer NOT NULL,
    original_size_bytes integer NOT NULL,
    naive_size_bytes integer NOT NULL,
    accurate_size_bytes integer NOT NULL,
    accurate_points_count integer NOT NULL,
    naive_to_original_mse real NOT NULL,
    original_to_naive_mse real NOT NULL,
    accurate_to_original_mse real NOT NULL,
    original_to_accurate_mse real NOT NULL,
    naive_to_original_rmse real NOT NULL,
    original_to_naive_rmse real NOT NULL,
    accurate_to_original_rmse real NOT NULL,
    original_to_accurate_rmse real NOT NULL
);
CREATE INDEX compression_frame_result_experiment_id_idx ON compression_frame_result (experiment_id);
CREATE INDEX compression_frame_result_experiment_id_dataset_frame_id_idx ON compression_frame_result (experiment_id, dataset_frame_id);

CREATE TABLE ri_experiment
(
    id integer PRIMARY KEY AUTOINCREMENT,
    timestamp text NOT NULL,
    label text NOT NULL,
    description text NOT NULL,
    commit_hash text NULL
);

CREATE TABLE ri_frame_result
(
    id integer PRIMARY KEY AUTOINCREMENT NOT NULL,
    experiment_id integer NOT NULL REFERENCES ri_experiment (id),
    dataset_frame_id integer NOT NULL REFERENCES dataset_frame (id),
    method text NOT NULL,
    ri_width integer NOT NULL,
    ri_height integer NOT NULL,
    original_points_count real NOT NULL,
    reconstructed_points_count real NOT NULL,
    reconstructed_to_original_mse real NOT NULL,
    original_to_reconstructed_mse real NOT NULL,
    reconstructed_to_original_rmse real NOT NULL,
    original_to_reconstructed_rmse real NOT NULL
);
CREATE INDEX ri_frame_result_experiment_id_idx ON ri_frame_result (experiment_id);
CREATE INDEX ri_frame_result_experiment_id_dataset_frame_id_idx ON ri_frame_result (experiment_id, dataset_frame_id);
