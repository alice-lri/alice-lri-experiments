import glob
from ...common.helper.orm import *
from ...common.helper.entities import *
from ...common.helper.datasets.kitti import *
from ...common.helper.datasets.durlar import *
from ...common.helper.ground_truth import *
import os

from dotenv import load_dotenv
load_dotenv()

class DatasetConfiguration:
    info: Dataset
    base_path: str
    frames_glob: str
    first_frame_path: str

    def __init__(self, info: Dataset, base_path: str, frames_glob: str, first_frame_path: str):
        self.info = info
        self.base_path = base_path
        self.frames_glob = frames_glob
        self.first_frame_path = first_frame_path

class Config:
    datasets_frames: dict[str, tuple[Dataset, str]] = {
        "kitti": DatasetConfiguration(
            KITTI(),
            os.getenv("KITTI_ROOT"),
            "*/*/velodyne_points/data/*.bin",
            "2011_09_26/2011_09_26_drive_0001_sync/velodyne_points/data/0000000000.bin",
        ),
        "durlar": DatasetConfiguration(
            DurLAR(),
            os.getenv("DURLAR_ROOT"),
            "*/ouster_points/data/*.bin",
            "DurLAR_20210716/ouster_points/data/0000000000.bin",
        )
    }

def main():
    with Database(os.getenv("SQLITE_DB")) as db:
        for d_name, d_configuration in Config.datasets_frames.items():
            dataset = DatasetEntity(name=d_name, laser_count=d_configuration.info.laser_count)
            dataset.save(db)

            frames_paths = glob.glob(os.path.join(d_configuration.base_path, d_configuration.frames_glob))
            frames_rel_paths = [os.path.relpath(path, d_configuration.base_path) for path in frames_paths]
            frames = [DatasetFrame(dataset_id=dataset.id, relative_path=path) for path in frames_rel_paths]

            DatasetFrame.save_all(db, frames)

            points, _ = load_binary(os.path.join(d_configuration.base_path, d_configuration.first_frame_path))
            points = points[calculate_range(points) > 0]

            d_info = d_configuration.info
            _, gt_result = compute_ground_truth(
                points, d_info.v_angles, d_info.v_offsets, d_info.h_offsets, d_info.h_resolutions
            )

            for gt_scanline in gt_result["scanlines"]:
                gt_entity = DatasetLaserGt(
                    dataset_id=dataset.id,
                    laser_idx=gt_scanline['laser_idx'],
                    vertical_offset=gt_scanline['v_offset'],
                    vertical_angle=gt_scanline['v_angle'],
                    horizontal_offset=gt_scanline['h_offset'],
                    horizontal_resolution=gt_scanline['h_resolution'],
                    horizontal_angle_offset=gt_scanline['theta_offset']
                )
                gt_entity.save(db)


if __name__ == "__main__":
    main()

