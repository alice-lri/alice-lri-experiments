from typing import Union
from orm import OrmEntity, SQLExpr


class DatasetEntity(OrmEntity, table_name="dataset"):
    id: int
    name: str
    laser_count: int

class DatasetFrame(OrmEntity, table_name="dataset_frame"):
    id: int
    dataset_id: int
    relative_path: str

class DatasetLaserGt(OrmEntity, table_name="dataset_laser_gt"):
    id: int
    dataset_id: int
    laser_idx: int
    vertical_offset: float
    vertical_angle: float
    horizontal_offset: float
    horizontal_resolution: float
    horizontal_angle_offset: float

class DatasetFrameScanlineGt(OrmEntity, table_name="dataset_frame_scanline_gt"):
    id: int
    dataset_frame_id: int
    laser_id: int
    scanline_idx: int

class IntrinsicsExperiment(OrmEntity, table_name="intrinsics_experiment"):
    id: int
    timestamp: Union[int, SQLExpr]
    label: str
    description: str
    commit_hash: str
    use_hough_continuity: bool
    use_scanline_conflict_solver: bool
    use_vertical_heuristics: bool
    use_horizontal_heuristics: bool

class RangeImageExperiment(OrmEntity, table_name="ri_experiment"):
    id: int
    timestamp: Union[int, SQLExpr]
    label: str
    description: str
    commit_hash: str

class CompressionExperiment(OrmEntity, table_name="compression_experiment"):
    id: int
    timestamp: Union[int, SQLExpr]
    label: str
    description: str
    commit_hash: str