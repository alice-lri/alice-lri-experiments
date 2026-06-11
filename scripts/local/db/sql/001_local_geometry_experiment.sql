CREATE TABLE IF NOT EXISTS local_geometry_experiment
(
    id integer PRIMARY KEY AUTOINCREMENT,
    timestamp text NOT NULL,
    label text NOT NULL,
    description text NOT NULL,
    commit_hash text NULL
);

CREATE TABLE IF NOT EXISTS local_geometry_frame_result
(
    id integer PRIMARY KEY AUTOINCREMENT NOT NULL,
    experiment_id integer NOT NULL REFERENCES local_geometry_experiment (id),
    dataset_frame_id integer NOT NULL REFERENCES dataset_frame (id),
    method text NOT NULL,
    ri_width integer NOT NULL,
    ri_height integer NOT NULL,
    original_points_count integer NOT NULL,
    reconstructed_points_count integer NOT NULL,
    k_neighbors integer NOT NULL,
    runtime_seconds real NOT NULL,
    metrics_runtime_seconds real NOT NULL,
    reconstructed_to_original_point_to_plane_mean real NOT NULL,
    reconstructed_to_original_point_to_plane_rmse real NOT NULL,
    reconstructed_to_original_point_to_plane_median real NOT NULL,
    reconstructed_to_original_point_to_plane_p95 real NOT NULL,
    reconstructed_to_original_point_to_plane_max real NOT NULL,
    original_to_reconstructed_point_to_plane_mean real NOT NULL,
    original_to_reconstructed_point_to_plane_rmse real NOT NULL,
    original_to_reconstructed_point_to_plane_median real NOT NULL,
    original_to_reconstructed_point_to_plane_p95 real NOT NULL,
    original_to_reconstructed_point_to_plane_max real NOT NULL,
    point_to_plane_mean real NOT NULL,
    point_to_plane_rmse real NOT NULL,
    point_to_plane_median real NOT NULL,
    point_to_plane_p95 real NOT NULL,
    point_to_plane_max real NOT NULL,

    UNIQUE (experiment_id, dataset_frame_id, method)
);
CREATE INDEX IF NOT EXISTS local_geometry_frame_result_experiment_id_idx
    ON local_geometry_frame_result (experiment_id);
CREATE INDEX IF NOT EXISTS local_geometry_frame_result_experiment_id_dataset_frame_id_idx
    ON local_geometry_frame_result (experiment_id, dataset_frame_id);
