import os

import alice_lri
import numpy as np

from scripts.common.helper.point_cloud import load_binary
from scripts.common.helper.ri.ri_default_mapper import RangeImageDefaultMapper
from scripts.common.helper.ri.ri_utils import point_cloud_to_range_image, range_image_to_point_cloud
from scripts.common.load_env import load_env
from scripts.local.paper.helper.utils import save_point_cloud_visualization, save_range_image

load_env()

class Config:
    class Reconstruction:
        __ESTIMATION_CLOUD_PATH = "2011_09_26/2011_09_26_drive_0009_sync/velodyne_points/data/0000000000.bin"
        ESTIMATION_CLOUD_PATH = os.path.join(os.getenv("LOCAL_KITTI_PATH"), __ESTIMATION_CLOUD_PATH)

        __TARGET_CLOUD_PATH = "2011_09_26/2011_09_26_drive_0009_sync/velodyne_points/data/0000000160.bin"
        TARGET_CLOUD_PATH = os.path.join(os.getenv("LOCAL_KITTI_PATH"), __TARGET_CLOUD_PATH)

        ORIGINAL_OUT_IMAGE_PATH = os.path.join(os.getenv("PAPER_FIGURES_DIR"), "kitti_3d_original.png")
        PBEA_OUT_IMAGE_PATH = os.path.join(os.getenv("PAPER_FIGURES_DIR"), "kitti_3d_pbea.png")
        ALICE_OUT_IMAGE_PATH = os.path.join(os.getenv("PAPER_FIGURES_DIR"), "kitti_3d_alice.png")

    class Visualization:
        __ESTIMATION_CLOUD_PATH = "DurLAR_20210901/ouster_points/data/0000000000.bin"
        ESTIMATION_CLOUD_PATH = os.path.join(os.getenv("LOCAL_DURLAR_PATH"), __ESTIMATION_CLOUD_PATH)

        __TARGET_CLOUD_PATH = "DurLAR_20211209/ouster_points/data/0000007398.bin"
        TARGET_CLOUD_PATH = os.path.join(os.getenv("LOCAL_DURLAR_PATH"), __TARGET_CLOUD_PATH)

        PBEA_OUT_IMAGE_PATH = os.path.join(os.getenv("PAPER_FIGURES_DIR"), "range_image_pbea.pdf")
        ALICE_OUT_IMAGE_PATH = os.path.join(os.getenv("PAPER_FIGURES_DIR"), "range_image_alice.pdf")


def main():
    print("Generating reconstruction figures...")
    generate_reconstruction_figures()

    print("Generating range image figures...")
    generate_range_image_figures()

    print("All done.")


def generate_reconstruction_figures():
    intrinsics, points = load_intrinsics_and_points(
        Config.Reconstruction.ESTIMATION_CLOUD_PATH, Config.Reconstruction.TARGET_CLOUD_PATH
    )

    print(" - Projecting/Unprojecting range images...")
    pbea_ri_mapper = RangeImageDefaultMapper(4000, 64)
    pbea_ri = point_cloud_to_range_image(pbea_ri_mapper, points)
    pbea_cloud = range_image_to_point_cloud(pbea_ri_mapper, pbea_ri)

    x, y, z = points[:, 0], points[:, 1], points[:, 2]
    alice_ri = alice_lri.project_to_range_image(intrinsics, x, y, z)
    x_r, y_r, z_r = alice_lri.unproject_to_point_cloud(intrinsics, alice_ri)
    alice_cloud = np.column_stack((x_r, y_r, z_r))
    alice_cloud = np.round(alice_cloud, decimals=3)

    print(" - Writing output images...")
    view_args = { "cmap": "gray", "point_size": 20, "elev": 89, "azim": 182, "zoom": 4.5, "figure_size": (24,24) }
    save_point_cloud_visualization(Config.Reconstruction.ORIGINAL_OUT_IMAGE_PATH, points, np.ones_like(points[:, 0]), **view_args)
    save_point_cloud_visualization(Config.Reconstruction.PBEA_OUT_IMAGE_PATH, pbea_cloud, np.ones_like(pbea_cloud[:, 0]), **view_args)
    save_point_cloud_visualization(Config.Reconstruction.ALICE_OUT_IMAGE_PATH, alice_cloud, np.ones_like(alice_cloud[:, 0]), **view_args)

    print(" - Done")


def generate_range_image_figures():
    intrinsics, points = load_intrinsics_and_points(
        Config.Visualization.ESTIMATION_CLOUD_PATH, Config.Visualization.TARGET_CLOUD_PATH
    )

    print(" - Projecting/Unprojecting range images...")
    pbea_ri_mapper = RangeImageDefaultMapper(2048, 128)
    pbea_ri = point_cloud_to_range_image(pbea_ri_mapper, points)

    x, y, z = points[:, 0], points[:, 1], points[:, 2]
    alice_ri = alice_lri.project_to_range_image(intrinsics, x, y, z)

    print(" - Writing output images...")
    save_range_image(Config.Visualization.PBEA_OUT_IMAGE_PATH, pbea_ri, (pbea_ri_mapper.min_phi, pbea_ri_mapper.max_phi), origin="lower", show_colorbar=False)
    save_alice_ri(alice_ri, intrinsics)

    print(" - Done")


def load_intrinsics_and_points(estimation_path: str, target_path:str) -> tuple[alice_lri.Intrinsics, np.ndarray]:
    print(" - Estimating ALICE-LRI intrinsics...")

    points, _ = load_binary(estimation_path)
    x, y, z = points[:, 0], points[:, 1], points[:, 2]
    intrinsics = alice_lri.estimate_intrinsics(x, y, z)

    points, _ = load_binary(target_path)
    return intrinsics, points


def save_alice_ri(ri: alice_lri.RangeImage, intrinsics: alice_lri.Intrinsics):
    width = ri.width
    height = ri.height
    pixels = np.array(ri)
    min_phi = intrinsics.scanlines[0].vertical_angle
    max_phi = intrinsics.scanlines[-1].vertical_angle

    pixels = np.array(pixels)
    pixels = pixels.reshape((height, width))

    return save_range_image(Config.Visualization.ALICE_OUT_IMAGE_PATH, pixels, (min_phi, max_phi), origin="upper", show_colorbar=False)


if __name__ == "__main__":
    main()