import glob
from scripts.common.helper.orm import *
from scripts.common.helper.entities import *
from scripts.common.helper.datasets.kitti import *
from scripts.common.helper.datasets.durlar import *
from scripts.common.helper.ground_truth import *
import os

from scripts.common.load_env import load_env
load_env()

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
            os.getenv("LOCAL_KITTI_PATH"),
            "*/*/velodyne_points/data/*.bin",
            "2011_09_26/2011_09_26_drive_0001_sync/velodyne_points/data/0000000000.bin",
        ),
        "durlar": DatasetConfiguration(
            DurLAR(),
            os.getenv("LOCAL_DURLAR_PATH"),
            "*/ouster_points/data/*.bin",
            "DurLAR_20210716/ouster_points/data/0000000000.bin",
        )
    }

def main():
    db_path = os.getenv("LOCAL_SQLITE_DB")
    print(f"Will populate base entities in the database {db_path}")

    with Database(db_path) as db:
        for d_name, d_configuration in Config.datasets_frames.items():
            print(f"Populating for dataset: {d_name}")
            dataset = DatasetEntity(name=d_name, laser_count=d_configuration.info.laser_count)
            dataset.save(db)

            print(" - Adding frames...")
            frames_paths = glob.glob(os.path.join(d_configuration.base_path, d_configuration.frames_glob))
            frames_rel_paths = [os.path.relpath(path, d_configuration.base_path) for path in frames_paths]
            frames = [DatasetFrame(dataset_id=dataset.id, relative_path=path) for path in frames_rel_paths]

            DatasetFrame.save_all(db, frames)

            print(" - Adding ground truth values...")
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

    print("Database population completed.")


if __name__ == "__main__":
    main()

