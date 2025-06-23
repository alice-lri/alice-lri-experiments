import os
import glob
import random
import subprocess
import numpy as np
import pandas as pd
import open3d as o3d
import shutil
import argparse
import accurate_ri


class Config:
    naive_encoder_exec = "../../rtst/src/pcc_encoder"
    accurate_encoder_exec = "../../rtst-modified/build/pcc_encoder_accurate"
    naive_decoder_exec = "../../rtst/src/pcc_decoder"
    accurate_decoder_exec = "../../rtst-modified/build/pcc_decoder_accurate"
    accurate_ri_lib_path = "../../accurate-ri/build/lib"
    horizontal_step = "0.09"
    vertical_step = "0.45"
    fmt = "binary"
    tile_size = "4"
    error_thresholds = [0.001, 0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 1]
    out_path = "data"
    cwd = "../"
    results_file = "results.csv"


def load_binary(file_path):
    data = np.fromfile(file_path, dtype=np.float32).reshape((-1, 4))
    return data[:, :3], data[:, 3]


def chamfer_distance(pc1, pc2):
    pcd1 = o3d.geometry.PointCloud()
    pcd2 = o3d.geometry.PointCloud()
    pcd1.points = o3d.utility.Vector3dVector(pc1)
    pcd2.points = o3d.utility.Vector3dVector(pc2)
    dists1 = pcd1.compute_point_cloud_distance(pcd2)
    dists2 = pcd2.compute_point_cloud_distance(pcd1)
    return (np.mean(dists1) + np.mean(dists2)) / 2, dists1, dists2


def run_process(cmd, cwd, env):
    subprocess.run(cmd, check=True, cwd=cwd, env=env)


def get_file_size(path):
    return os.path.getsize(path)


def create_output_path(decoded_path):
    os.makedirs(os.path.dirname(decoded_path), exist_ok=True)


def build_naive_encoder_cmd(input_dir, input_file, output_file, error_threshold):
    return [
        os.path.abspath(Config.naive_encoder_exec),
        "--path", input_dir,
        "--file", input_file,
        "-p", Config.horizontal_step,
        "-y", Config.vertical_step,
        "-f", Config.fmt,
        "-l", Config.tile_size,
        "-t", str(error_threshold),
        "--out", output_file
    ]


def build_accurate_encoder_cmd(input_dir, input_file, intrinsics_file, output_file, error_threshold):
    return [
        os.path.abspath(Config.accurate_encoder_exec),
        "--path", input_dir,
        "--file", input_file,
        "-i", intrinsics_file,
        "-f", Config.fmt,
        "-l", Config.tile_size,
        "-t", str(error_threshold),
        "--out", output_file
    ]


def build_naive_decoder_cmd(input_file):
    return [
        os.path.abspath(Config.naive_decoder_exec),
        "-p", Config.horizontal_step,
        "-y", Config.vertical_step,
        "-f", Config.fmt,
        "-l", Config.tile_size,
        "--file", input_file
    ]


def build_accurate_decoder_cmd(input_file, intrinsics_file):
    return [
        os.path.abspath(Config.accurate_decoder_exec),
        "-i", intrinsics_file,
        "-f", Config.fmt,
        "-l", Config.tile_size,
        "--file", input_file
    ]


def run_single(args, env):
    train_parts = args.train.split(":")
    target_parts = args.target.split(":")
    train_root = args.kitti_root if train_parts[0] == "kitti" else args.durlar_root
    target_root = args.kitti_root if target_parts[0] == "kitti" else args.durlar_root
    train_path = os.path.join(train_root, train_parts[1])
    target_path = os.path.join(target_root, target_parts[1])

    print("Loading train points from:", train_path)
    train_points, _ = load_binary(train_path)

    print("Loading target points from:", target_path)
    target_points, _ = load_binary(target_path)
    original_size = get_file_size(target_path)

    working_dir = "/tmp"

    print("Training...")
    intrinsics = accurate_ri.train(train_points[:, 0], train_points[:, 1], train_points[:, 2])
    intrinsics_file = os.path.join(working_dir, "intrinsics.json")
    accurate_ri.write_to_json(intrinsics, intrinsics_file)

    target_dir = os.path.dirname(target_path)
    target_filename = os.path.basename(target_path)
    out_filename = "out.tar.gz"

    for error_threshold in Config.error_thresholds:
        print(f"Error threshold: {error_threshold}")

        encoder_cmd = build_naive_encoder_cmd(target_dir, target_filename, out_filename, error_threshold)
        run_process(encoder_cmd, working_dir, env)
        naive_size = get_file_size(os.path.join(working_dir, out_filename))
        decoder_cmd = build_naive_decoder_cmd(out_filename)
        run_process(decoder_cmd, working_dir, env)
        naive_points, _ = load_binary(os.path.join(working_dir, target_filename))

        encoder_cmd = build_accurate_encoder_cmd(target_dir, target_filename, intrinsics_file, out_filename,
                                                 error_threshold)
        run_process(encoder_cmd, working_dir, env)
        accurate_size = get_file_size(os.path.join(working_dir, out_filename))
        decoder_cmd = build_accurate_decoder_cmd(out_filename, intrinsics_file)
        run_process(decoder_cmd, working_dir, env)
        accurate_points, _ = load_binary(os.path.join(working_dir, target_filename))

        cr_naive = original_size / naive_size
        cr_accurate = original_size / accurate_size

        cd_naive, _, _ = chamfer_distance(target_points, naive_points)
        cd_accurate, _, _ = chamfer_distance(target_points, accurate_points)

        print(f"Compression Ratio (Naive): {cr_naive:.2f}")
        print(f"Chamfer distance (Naive): {cd_naive:.6f}")
        print(f"Compression Ratio (Accurate): {cr_accurate:.2f}")
        print(f"Chamfer distance (Accurate): {cd_accurate:.6f}")


def parse_args():
    parser = argparse.ArgumentParser(description="Compare naive and accurate point cloud compression.")
    parser.add_argument("--mode", required=True, choices=["batch", "single"], help="Mode: batch or single.")
    parser.add_argument("--task_id", type=int, default=None, help="Task ID (optional).")
    parser.add_argument("--task_count", type=int, default=None, help="Task count (optional).")
    parser.add_argument("--db_path", type=str, default=None, help="Path to the database file (optional).")
    parser.add_argument("--train", type=str, default=None, help="Train path (optional).")
    parser.add_argument("--target", type=str, default=None, help="Target path (optional).")
    parser.add_argument("--kitti_root", required=True, help="Path to KITTI dataset root directory.")
    parser.add_argument("--durlar_root", required=True, help="Path to DURLAR dataset root directory.")
    args = parser.parse_args()

    if args.mode == "batch":
        if args.task_id is None or args.task_count is None or args.db_path is None:
            parser.error("--task_id, --task_count, and --db_path are required in batch mode.")
    else:
        if args.train is None or args.target is None:
            parser.error("--train and --target are required in single mode.")

        train_parts = args.train.split(":")
        target_parts = args.target.split(":")

        if len(train_parts) != 2 or train_parts[0] not in ["kitti", "durlar"]:
            parser.error("Invalid format for --train. Expected 'dataset:path'")

        if len(target_parts) != 2 or target_parts[0] not in ["kitti", "durlar"]:
            parser.error("Invalid format for --target. Expected 'dataset:path'")

    return args


def main():
    args = parse_args()

    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = os.path.abspath(Config.accurate_ri_lib_path)

    if args.mode == "single":
        run_single(args, env)
    else:
        kitti_sequences = glob.glob(os.path.join(args.kitti_root, "*/*/velodyne_points/data"))
        durlar_sequences = glob.glob(os.path.join(args.durlar_root, "*/ouster_points/data"))


if __name__ == "__main__":
    main()
