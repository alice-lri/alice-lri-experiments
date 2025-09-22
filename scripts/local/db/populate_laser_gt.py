from dotenv import load_dotenv
from ...common.helper.datasets.base import Dataset
from ...common.helper.datasets.durlar import DurLAR
from ...common.helper.datasets.kitti import KITTI
from ...common.helper.orm import *
from ...common.helper.entities import *
from ...common.helper.ground_truth import *

load_dotenv()
import os

class Config:
    datasets_frames: dict[str, tuple[Dataset, str]] = {
        "kitti": (KITTI(), os.path.join(os.getenv("KITTI_ROOT"), "2011_09_26/2011_09_26_drive_0001_sync/velodyne_points/data/0000000000.bin")),
        "durlar": (DurLAR(), os.path.join(os.getenv("DURLAR_ROOT"), "DurLAR_20210716/ouster_points/data/0000000000.bin")),
    }


def main():
    with Database(os.getenv("SQLITE_DB")) as db:
        datasets = DatasetEntity.all(db)

        for dataset_entity in datasets:
            dataset_data, frame_path = Config.datasets_frames[dataset_entity.name]
            points, _ = load_binary(frame_path)
            points = points[calculate_range(points) > 0]

            _, gt_result = compute_ground_truth(
                points, dataset_data.v_angles, dataset_data.v_offsets, dataset_data.h_offsets, dataset_data.h_resolutions
            )
            for gt_scanline in gt_result["scanlines"]:
                gt_entity = DatasetLaserGt(
                    dataset_id=dataset_entity.id,
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

