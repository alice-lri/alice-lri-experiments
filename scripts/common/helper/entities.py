from typing import Union
from orm import OrmEntity, SQLExpr


class DatasetEntity(OrmEntity, table_name="dataset"):
    id: int | None
    name: str
    laser_count: int

class DatasetFrame(OrmEntity, table_name="dataset_frame"):
    id: int | None
    dataset_id: int
    relative_path: str

class DatasetLaserGt(OrmEntity, table_name="dataset_laser_gt"):
    id: int | None
    dataset_id: int
    laser_idx: int
    vertical_offset: float
    vertical_angle: float
    horizontal_offset: float
    horizontal_resolution: float
    horizontal_angle_offset: float

class DatasetFrameGt(OrmEntity, table_name="dataset_frame_gt"):
    id: int | None
    dataset_frame_id: int
    points_count: int
    scanlines_count: int

class DatasetFrameScanlineGt(OrmEntity, table_name="dataset_frame_scanline_gt"):
    id: int | None
    dataset_frame_id: int
    laser_id: int
    scanline_idx: int

class IntrinsicsExperiment(OrmEntity, table_name="intrinsics_experiment"):
    id: int | None
    timestamp: Union[int, SQLExpr]
    label: str
    description: str
    commit_hash: str
    use_hough_continuity: bool
    use_scanline_conflict_solver: bool
    use_vertical_heuristics: bool
    use_horizontal_heuristics: bool

class IntrinsicsFrameResult(OrmEntity, table_name="intrinsics_frame_result"):
    id: int | None
    experiment_id: int
    dataset_frame_id: int
    points_count: int
    scanlines_count: int
    vertical_iterations: int
    unassigned_points: int
    end_reason: str

class IntrinsicsScanlineResult(OrmEntity, table_name="intrinsics_scanline_result"):
    id: int | None
    intrinsics_result_id: int
    scanline_idx: int
    points_count: int
    vertical_offset: float
    vertical_angle: float
    vertical_ci_offset_lower: float
    vertical_ci_offset_upper: float
    vertical_ci_angle_lower: float
    vertical_ci_angle_upper: float
    vertical_theoretical_angle_bottom_lower: float
    vertical_theoretical_angle_bottom_upper: float
    vertical_theoretical_angle_top_lower: float
    vertical_theoretical_angle_top_upper: float
    vertical_uncertainty: float
    vertical_last_scanline: bool
    vertical_hough_votes: float
    vertical_hough_hash: str
    horizontal_offset: float
    horizontal_resolution: int
    horizontal_heuristic: bool
    horizontal_angle_offset: float

class RangeImageExperiment(OrmEntity, table_name="ri_experiment"):
    id: int | None
    timestamp: Union[int, SQLExpr]
    label: str
    description: str
    commit_hash: str

class RangeImageFrameResult(OrmEntity, table_name="ri_frame_result"):
    id: int | None
    experiment_id: int
    dataset_frame_id: int
    method: str
    ri_width: int
    ri_height: int
    original_points_count: float
    reconstructed_points_count: float
    reconstructed_to_original_mse: float
    original_to_reconstructed_mse: float
    reconstructed_to_original_rmse: float
    original_to_reconstructed_rmse: float

class CompressionExperiment(OrmEntity, table_name="compression_experiment"):
    id: int | None
    timestamp: Union[int, SQLExpr]
    label: str
    description: str
    commit_hash: str

class CompressionFrameResult(OrmEntity, table_name="compression_frame_result"):
    id: int | None
    experiment_id: int
    dataset_frame_id: int
    horizontal_step: float
    vertical_step: float
    tile_size: int
    error_threshold: float
    original_points_count: int
    naive_points_count: int
    original_size_bytes: int
    naive_size_bytes: int
    accurate_size_bytes: int
    accurate_points_count: int
    naive_to_original_mse: float
    original_to_naive_mse: float
    accurate_to_original_mse: float
    original_to_accurate_mse: float
    naive_to_original_rmse: float
    original_to_naive_rmse: float
    accurate_to_original_rmse: float
    original_to_accurate_rmse: float
