import os
import re
import sqlite3
import subprocess
import numpy as np
import pandas as pd
import open3d as o3d
import argparse
import accurate_ri


class Config:
    naive_encoder_exec = "../../rtst/src/pcc_encoder"
    accurate_encoder_exec = "../../rtst-modified/build/pcc_encoder_accurate"
    naive_decoder_exec = "../../rtst/src/pcc_decoder"
    accurate_decoder_exec = "../../rtst-modified/build/pcc_decoder_accurate"
    accurate_ri_lib_path = "../../accurate-ri/build/lib"
    fmt = "binary"
    tile_size = "4"
    error_thresholds = [0.001, 0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 1]
    working_dir = "/tmp"
    results_file = "results.csv"
    dataset = None

    __kitti_horizontal_step = "0.09009"
    __kitti_vertical_step = "0.47"
    __durlar_horizontal_step = "0.1761"
    __durlar_vertical_step = "0.235"

    @staticmethod
    def get_horizontal_step():
        return Config.__kitti_horizontal_step if Config.dataset == "kitti" else Config.__durlar_horizontal_step

    @staticmethod
    def get_vertical_step():
        return Config.__kitti_vertical_step if Config.dataset == "kitti" else Config.__durlar_vertical_step


class Globals:
    env = None


def load_binary(file_path):
    data = np.fromfile(file_path, dtype=np.float32).reshape((-1, 4))
    return data[:, :3], data[:, 3]


def compute_p_cloud_mse(pc1, pc2):
    pcd1 = o3d.geometry.PointCloud()
    pcd2 = o3d.geometry.PointCloud()

    pcd1.points = o3d.utility.Vector3dVector(pc1)
    pcd2.points = o3d.utility.Vector3dVector(pc2)

    dists1 = pcd1.compute_point_cloud_distance(pcd2)
    dists2 = pcd2.compute_point_cloud_distance(pcd1)

    return np.mean(np.array(dists1)**2), np.mean(np.array(dists2)**2)


def run_process(cmd):
    subprocess.run(cmd, check=True, cwd=Config.working_dir, env=Globals.env)


def get_file_size(path):
    return os.path.getsize(path)


def create_output_path(decoded_path):
    os.makedirs(os.path.dirname(decoded_path), exist_ok=True)


def get_frame_path(args, dataset, relative_path):
    dataset_root = args.kitti_root if dataset == "kitti" else args.durlar_root
    frame_path = os.path.join(dataset_root, relative_path)

    return frame_path


def build_naive_encoder_cmd(input_dir, input_file, output_file, error_threshold):
    return [
        os.path.abspath(Config.naive_encoder_exec),
        "--path", input_dir,
        "--file", input_file,
        "-p", Config.get_horizontal_step(),
        "-y", Config.get_vertical_step(),
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
        "-p", Config.get_horizontal_step(),
        "-y", Config.get_vertical_step(),
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


def train(train_path, intrinsics_file):
    print("Loading train points from:", train_path)
    train_points, _ = load_binary(train_path)

    print("Training...")
    intrinsics = accurate_ri.train(train_points[:, 0], train_points[:, 1], train_points[:, 2])
    accurate_ri.write_to_json(intrinsics, intrinsics_file)


def evaluate_compression(dataset, target_path, intrinsics_file, out_filename):
    Config.dataset = dataset
    target_dir = os.path.dirname(target_path)
    target_filename = os.path.basename(target_path)
    df_rows = []

    print("Loading target points from:", target_path)
    target_points, _ = load_binary(target_path)
    original_size = get_file_size(target_path)
    for error_threshold in Config.error_thresholds:
        print(f"Error threshold: {error_threshold}")

        encoder_cmd = build_naive_encoder_cmd(target_dir, target_filename, out_filename, error_threshold)
        run_process(encoder_cmd)
        naive_size = get_file_size(os.path.join(Config.working_dir, out_filename))
        decoder_cmd = build_naive_decoder_cmd(out_filename)
        run_process(decoder_cmd)
        naive_points, _ = load_binary(os.path.join(Config.working_dir, target_filename))

        encoder_cmd = build_accurate_encoder_cmd(target_dir, target_filename, intrinsics_file, out_filename,
                                                 error_threshold)
        run_process(encoder_cmd)
        accurate_size = get_file_size(os.path.join(Config.working_dir, out_filename))
        decoder_cmd = build_accurate_decoder_cmd(out_filename, intrinsics_file)
        run_process(decoder_cmd)
        accurate_points, _ = load_binary(os.path.join(Config.working_dir, target_filename))

        cr_naive = original_size / naive_size
        cr_accurate = original_size / accurate_size

        naive_to_original_mse, original_to_naive_mse = compute_p_cloud_mse(naive_points, target_points)
        accurate_to_original_mse, original_to_accurate_mse = compute_p_cloud_mse(accurate_points, target_points)

        print(f"Compression Ratio (Naive): {cr_naive}")
        print(f"MSE (Naive to Original): {naive_to_original_mse}")
        print(f"MSE (Original to Naive): {original_to_naive_mse}")
        print(f"Compression Ratio (Accurate): {cr_accurate}")
        print(f"MSE (Accurate to Original): {accurate_to_original_mse}")
        print(f"MSE (Original to Accurate): {original_to_accurate_mse}")

        df_rows.append({
            "horizontal_step": Config.get_horizontal_step(),
            "vertical_step": Config.get_vertical_step(),
            "tile_size": Config.tile_size,
            "error_threshold": error_threshold,
            "original_points_count": target_points.shape[0],
            "naive_points_count": naive_points.shape[0],
            "accurate_points_count": accurate_points.shape[0],
            "original_size_bytes": original_size,
            "naive_size_bytes": naive_size,
            "accurate_size_bytes": accurate_size,
            "naive_to_original_mse": naive_to_original_mse,
            "original_to_naive_mse": original_to_naive_mse,
            "accurate_to_original_mse": accurate_to_original_mse,
            "original_to_accurate_mse": original_to_accurate_mse,
        })

    return pd.DataFrame(df_rows)


def run_single(args):
    train_parts = args.train.split(":")
    target_parts = args.target.split(":")
    train_path = get_frame_path(args, train_parts[0], train_parts[1])
    target_path = get_frame_path(args, target_parts[0], target_parts[1])

    intrinsics_file = os.path.join(Config.working_dir, "intrinsics.json")
    train(train_path, intrinsics_file)

    out_filename = "out.tar.gz"

    df = evaluate_compression(target_parts[0], target_path, intrinsics_file, out_filename)

    df["train_dataset"] = train_parts[0]
    df["train_path"] = train_parts[1]
    df["target_dataset"] = target_parts[0]
    df["target_path"] = target_parts[1]

    df.to_csv(args.output_csv, index=False)


def run_batch(args):
    arg_datasets = []

    if args.kitti_root:
        arg_datasets.append("kitti")

    if args.durlar_root:
        arg_datasets.append("durlar")

    with sqlite3.connect(args.db_path) as conn:
        cur = conn.cursor()

        cur.execute("SELECT MAX(id) FROM compression_experiment")
        experiment_id = cur.fetchone()[0]

        assert experiment_id is not None, "Experiment ID must be defined."

        cur.execute("SELECT id, name FROM dataset")
        dataset_map = {id_: name for id_, name in cur.fetchall() if name in arg_datasets}

        assert dataset_map, "At least one dataset must be used."

        dataset_ids = list(dataset_map.keys())
        path_filter = "%0000000000.bin" if args.phase == "train" else "%"
        placeholders = ",".join(["?"] * len(dataset_ids))
        frames_query = f"""
            SELECT id, dataset_id, relative_path
            FROM dataset_frame
            WHERE id % ? == ?
            AND dataset_id IN ({placeholders})
            AND relative_path LIKE ?
        """

        cur.execute(frames_query, (args.task_count, args.task_id, *dataset_ids, path_filter))
        frames = cur.fetchall()

        print(f"Number of frames: {len(frames)}")

        for frame_id, dataset_id, relative_path in frames:
            dataset = dataset_map[dataset_id]
            frame_path = get_frame_path(args, dataset, relative_path)

            if args.phase == "train":
                intrinsics_path = os.path.join(Config.working_dir, f"{relative_path}.json") #TODO shared
                train(frame_path, intrinsics_path)
            elif args.phase == "compress":
                corresponding_train_relative_path = re.sub(r"\d{10}\.bin$", "0000000000.bin", relative_path)
                intrinsics_path = os.path.join(Config.working_dir, f"{corresponding_train_relative_path}.json") #TODO
                compression_out_path = os.path.join(Config.working_dir, f"{relative_path}.tar.gz") #TODO prolly scratch

                df = evaluate_compression(dataset, frame_path, intrinsics_path, compression_out_path)
                df["experiment_id"] = experiment_id
                df["dataset_frame_id"] = frame_id

                df.to_sql("compression_frame_result", conn, if_exists="append", index=False)


def parse_args():
    parser = argparse.ArgumentParser(description="Compare naive and accurate point cloud compression.")
    parser.add_argument("--mode", required=True, choices=["batch", "single", "test"], help="Mode: batch or single.")
    parser.add_argument("--phase", default=None, choices=["train", "compress"], help="Execution phase (batch mode).")
    parser.add_argument("--task_id", type=int, default=None, help="Task ID (batch mode).")
    parser.add_argument("--task_count", type=int, default=None, help="Task count (batch mode).")
    parser.add_argument("--db_path", type=str, default=None, help="Path to the database file (batch mode).")
    parser.add_argument("--train", type=str, default=None, help="Train path (single mode).")
    parser.add_argument("--target", type=str, default=None, help="Target path (single mode).")
    parser.add_argument("--output_csv", type=str, default=None, help="Optional output CSV file (single mode).")
    parser.add_argument("--kitti_root", type=str, default=None, help="Path to KITTI dataset root directory (optional).")
    parser.add_argument("--durlar_root", type=str, default=None,
                        help="Path to DURLAR dataset root directory (optional).")
    args = parser.parse_args()

    if args.mode == "batch":
        if args.task_id is None or args.task_count is None or args.db_path is None:
            parser.error("--task_id, --task_count, and --db_path are required in batch mode.")
    else:
        if args.train is None or args.target is None or args.output_csv is None:
            parser.error("--train, --target, and --output_csv are required in single mode.")

        train_parts = args.train.split(":")
        target_parts = args.target.split(":")

        if len(train_parts) != 2 or train_parts[0] not in ["kitti", "durlar"]:
            parser.error("Invalid format for --train. Expected 'dataset:path'")

        if len(target_parts) != 2 or target_parts[0] not in ["kitti", "durlar"]:
            parser.error("Invalid format for --target. Expected 'dataset:path'")

    if not args.kitti_root and not args.durlar_root:
        parser.error("At least one of --kitti_root or --durlar_root must be defined.")

    return args


def main():
    args = parse_args()

    Globals.env = os.environ.copy()
    Globals.env["LD_LIBRARY_PATH"] = os.path.abspath(Config.accurate_ri_lib_path)

    if args.mode == "single":
        run_single(args)
    elif args.mode == "batch":
        run_batch(args)
    elif args.mode == "test":
        print("If you see no errors, all is good.")
    else:
        raise ValueError("Unknown mode '{}'".format(args.mode))


if __name__ == "__main__":
    main()
