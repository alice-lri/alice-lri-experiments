import os

import alice_lri
import numpy as np

from scripts.common.helper.point_cloud import load_binary
from scripts.common.helper.ri.ri_default_mapper import RangeImageDefaultMapper
from scripts.common.helper.ri.ri_utils import point_cloud_to_range_image, range_image_to_point_cloud
from scripts.common.load_env import load_env
from scripts.local.paper.helper.utils import save_point_cloud_visualization

load_env()

class Config:
    __ESTIMATION_CLOUD_PATH = "2011_09_26/2011_09_26_drive_0009_sync/velodyne_points/data/0000000000.bin"
    ESTIMATION_CLOUD_PATH = os.path.join(os.getenv("LOCAL_KITTI_PATH"), __ESTIMATION_CLOUD_PATH)

    __TARGET_CLOUD_PATH = "2011_09_26/2011_09_26_drive_0009_sync/velodyne_points/data/0000000160.bin"
    TARGET_CLOUD_PATH = os.path.join(os.getenv("LOCAL_KITTI_PATH"), __TARGET_CLOUD_PATH)

    ORIGINAL_OUT_IMAGE_PATH = os.path.join(os.getenv("PAPER_FIGURES_DIR"), "kitti_3d_original.png")
    PBEA_OUT_IMAGE_PATH = os.path.join(os.getenv("PAPER_FIGURES_DIR"), "kitti_3d_pbea.png")
    ALICE_OUT_IMAGE_PATH = os.path.join(os.getenv("PAPER_FIGURES_DIR"), "kitti_3d_alice.png")


def main():
    print("Estimating ALICE-LRI intrinsics...")
    points, _ = load_binary(Config.ESTIMATION_CLOUD_PATH)
    x, y, z = points[:, 0], points[:, 1], points[:, 2]
    kitti_intrinsics = alice_lri.estimate_intrinsics(x, y, z)

    points, _ = load_binary(Config.TARGET_CLOUD_PATH)

    print("Projecting/Unprojecting range images...")
    kitti_ri_mapper = RangeImageDefaultMapper(4000, 64)
    naive_kitti_ri = point_cloud_to_range_image(kitti_ri_mapper, points)
    naive_kitti_reconstructed = range_image_to_point_cloud(kitti_ri_mapper, naive_kitti_ri)

    x, y, z = points[:, 0], points[:, 1], points[:, 2]
    better_kitti_ri = alice_lri.project_to_range_image(kitti_intrinsics, x, y, z)
    x_r, y_r, z_r = alice_lri.unproject_to_point_cloud(kitti_intrinsics, better_kitti_ri)
    better_kitti_reconstructed = np.column_stack((x_r, y_r, z_r))
    better_kitti_reconstructed = np.round(better_kitti_reconstructed, decimals=3)

    view_args = { "cmap": "gray", "point_size": 20, "elev": 89, "azim": 182, "zoom": 4.5, "figure_size": (24,24) }

    print("Writing output images...")
    save_point_cloud_visualization(Config.ORIGINAL_OUT_IMAGE_PATH, points, np.ones_like(points[:, 0]), **view_args)
    save_point_cloud_visualization(Config.PBEA_OUT_IMAGE_PATH, naive_kitti_reconstructed, np.ones_like(naive_kitti_reconstructed[:, 0]), **view_args)
    save_point_cloud_visualization(Config.ALICE_OUT_IMAGE_PATH, better_kitti_reconstructed, np.ones_like(better_kitti_reconstructed[:, 0]), **view_args)

    print("Done")


if __name__ == "__main__":
    main()