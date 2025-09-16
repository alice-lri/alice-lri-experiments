from dotenv import load_dotenv
from local.scripts.common.datasets.base import Dataset
from local.scripts.common.datasets.durlar import DurLAR
from local.scripts.common.datasets.kitti import KITTI
from local.scripts.common.orm import *
from local.scripts.common.point_cloud import *

load_dotenv()
import os

class Config:
    datasets_frames: dict[str, tuple[Dataset, str]] = {
        "kitti": (KITTI(), os.path.join(os.getenv("KITTI_ROOT"), "2011_09_26/2011_09_26_drive_0001_sync/velodyne_points/data/0000000000.bin")),
        "durlar": (DurLAR(), os.path.join(os.getenv("DURLAR_ROOT"), "DurLAR_20210716/ouster_points/data/0000000000.bin")),
    }


class DatasetEntity(OrmEntity, table_name="dataset"):
    id: int
    name: str
    laser_count: int


class DatasetLaserGt(OrmEntity, table_name="dataset_laser_gt"):
    id: int
    dataset_id: int
    laser_idx: int
    vertical_offset: float
    vertical_angle: float
    horizontal_offset: float
    horizontal_resolution: float
    horizontal_angle_offset: float


def main():
    db = Database(os.getenv("SQLITE_DB"))
    datasets = DatasetEntity.all(db)

    for dataset_entity in datasets:
        dataset_data, frame_path = Config.datasets_frames[dataset_entity.name]
        points, _ = load_binary(frame_path)
        points = points[calculate_range(points) > 0]

        _, gt_result = compute_ground_truth(points, dataset_data.v_angles, dataset_data.v_offsets, dataset_data.h_offsets, dataset_data.h_resolutions)
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

    db.close()


def compute_ground_truth(points, v_angles, v_offsets, h_offsets, h_resolutions, threshold=5e-4):
    assert np.all(np.diff(v_angles) > 0), "v_angles are not in ascending order"
    assert len(v_offsets) == len(v_angles), "v_offsets and v_angles have different lengths"

    phis = calculate_phi(points)
    thetas = calculate_theta(points)
    ranges = calculate_range(points)
    ranges_xy = calculate_range_xy(points)
    scanlines_ids = np.full(len(points), -1, dtype=int)
    theta_offsets = {}

    laser_idx = 0
    while laser_idx < len(v_offsets):
        v = v_offsets[laser_idx]
        phi_correction = np.arcsin(v / ranges)

        # find indices where correction was successful and phi is equal to the corresponding v_angle +- 1e-3
        idx = np.where(np.abs(phis - phi_correction - v_angles[laser_idx]) < threshold)[0]

        if len(idx) == 0:
            laser_idx += 1
            continue

        assert np.all(scanlines_ids[idx] == -1), "Some points were assigned to multiple scanlines"

        # assign scanline id to the corresponding indices
        scanlines_ids[idx] = laser_idx

        # compute diff to ideal and theta offset
        h = h_offsets[laser_idx]
        theta_step = 2 * np.pi / h_resolutions[laser_idx]
        corrected_thetas = thetas[idx] - np.arcsin(h / ranges_xy[idx])
        ideal_thetas = np.floor(corrected_thetas / theta_step) * theta_step
        theta_offsets[laser_idx] = float(np.mean(corrected_thetas - ideal_thetas))

        laser_idx += 1

    assert np.all(scanlines_ids != -1), "Some points were not assigned to any scanline"

    result = {
        'points_count': len(points),
        'scanlines_count': np.unique(scanlines_ids).shape[0],
        'scanlines': []
    }

    for laser_idx in np.unique(scanlines_ids):
        v_offset = v_offsets[laser_idx]
        v_angle = v_angles[laser_idx]
        h_offset = h_offsets[laser_idx]
        h_resolution = h_resolutions[laser_idx]

        points_count = int(np.sum(scanlines_ids == laser_idx))

        result['scanlines'].append({
            'laser_idx': int(laser_idx),
            'v_offset': v_offset,
            'v_angle': v_angle,
            'h_offset': h_offset,
            'h_resolution': h_resolution,
            'theta_offset': theta_offsets[laser_idx],
            'points_count': points_count
        })

    return scanlines_ids, result

if __name__ == "__main__":
    main()

