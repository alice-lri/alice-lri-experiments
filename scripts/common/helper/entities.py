from orm import OrmEntity

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
