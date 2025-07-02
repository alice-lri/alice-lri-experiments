import os
import re
import sqlite3
import subprocess

import pandas as pd
import open3d as o3d
import argparse
import accurate_ri
from common import *
from ri_default_mapper import RangeImageDefaultMapper


class Config:
    naive_encoder_exec = "../../rtst-modified/build/pcc_encoder"
    accurate_encoder_exec = "../../rtst-modified/build/pcc_encoder_accurate"
    naive_decoder_exec = "../../rtst-modified/build/pcc_decoder"
    accurate_decoder_exec = "../../rtst-modified/build/pcc_decoder_accurate"
    accurate_ri_lib_path = "../../accurate-ri/build/lib"
    fmt = "binary"
    tile_size = "4"
    error_thresholds = [0.001, 0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 1]
    ri_size_multipliers = [1, 2, 4, 8, 16, 32]
    methods = ["naive", "accurate"]
    private_dir = "/tmp"
    shared_dir = "/tmp"
    dataset = None
    experiment_type = None

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

    @staticmethod
    def get_result_sql_table():
        if Config.experiment_type == "ri":
            return "ri_frame_result"
        elif Config.experiment_type == "compression":
            return "compression_frame_result"
        else:
            raise ValueError("Unknown experiment type")


class Globals:
    env = None

def compute_p_cloud_mse(pc1, pc2):
    pcd1 = o3d.geometry.PointCloud()
    pcd2 = o3d.geometry.PointCloud()

    pcd1.points = o3d.utility.Vector3dVector(pc1)
    pcd2.points = o3d.utility.Vector3dVector(pc2)

    dists1 = pcd1.compute_point_cloud_distance(pcd2)
    dists2 = pcd2.compute_point_cloud_distance(pcd1)

    return np.mean(np.array(dists1)**2), np.mean(np.array(dists2)**2)


def run_process(cmd):
    subprocess.run(cmd, check=True, cwd=Config.private_dir, env=Globals.env)


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


def train(train_path, intrinsics_filename):
    print("Loading train points from:", train_path)
    train_points, _ = load_binary(train_path)

    print("Training...")
    intrinsics = accurate_ri.train(train_points[:, 0], train_points[:, 1], train_points[:, 2])

    intrinsics_file = os.path.join(Config.shared_dir, intrinsics_filename)
    accurate_ri.write_to_json(intrinsics, intrinsics_file)


def evaluate_ri(dataset, target_path, intrinsics_filename):
    Config.dataset = dataset
    intrinsics_file = os.path.join(Config.shared_dir, intrinsics_filename)
    df_rows = []

    print("Loading original points from:", target_path)
    points_original, _ = load_binary(target_path)
    x_original, y_original, z_original = points_original[:, 0], points_original[:, 1], points_original[:, 2]

    intrinsics = accurate_ri.read_from_json(intrinsics_file)

    print("Evaluating accurate method...")
    ri_accurate = accurate_ri.project_to_range_image(intrinsics, x_original, y_original, z_original)
    x_accurate, y_accurate, z_accurate = accurate_ri.unproject_to_point_cloud(intrinsics, ri_accurate)

    points_accurate = np.column_stack((x_accurate, y_accurate, z_accurate))
    accurate_to_original_mse, original_to_accurate_mse = compute_p_cloud_mse(points_accurate, points_original)

    df_rows.append({
        "method": "accurate",
        "ri_width": ri_accurate.width,
        "ri_height": ri_accurate.height,
        "original_points_count": points_original.shape[0],
        "reconstructed_points_count": points_accurate.shape[0],
        "reconstructed_to_original_mse": accurate_to_original_mse,
        "original_to_reconstructed_mse": original_to_accurate_mse,
    })

    for ri_size_multiplier in Config.ri_size_multipliers:
        ri_width = ri_accurate.width * ri_size_multiplier
        ri_height = ri_accurate.height * ri_size_multiplier

        print(f"Evaluating PBEA method ({ri_width}x{ri_height})...")

        ri_mapper = RangeImageDefaultMapper(ri_width, ri_height)

        pbea_ri = point_cloud_to_range_image(ri_mapper, points_original)
        points_pbea = range_image_to_point_cloud(ri_mapper, pbea_ri)

        pbea_to_original_mse, original_to_pbea_mse = compute_p_cloud_mse(points_pbea, points_original)

        df_rows.append({
            "method": "pbea",
            "ri_width": ri_width,
            "ri_height": ri_height,
            "original_points_count": points_original.shape[0],
            "reconstructed_points_count": points_pbea.shape[0],
            "reconstructed_to_original_mse": pbea_to_original_mse,
            "original_to_reconstructed_mse": original_to_pbea_mse,
        })

    return pd.DataFrame(df_rows)


def evaluate_compression(dataset, target_path, intrinsics_filename, out_filename):
    Config.dataset = dataset
    target_dir = os.path.dirname(target_path)
    target_filename = os.path.basename(target_path)
    intrinsics_file = os.path.join(Config.shared_dir, intrinsics_filename)
    df_rows = []

    print("Loading target points from:", target_path)
    target_points, _ = load_binary(target_path)
    original_size = get_file_size(target_path)
    for error_threshold in Config.error_thresholds:
        print(f"Error threshold: {error_threshold}")

        current_df_row = {}

        if "naive" in Config.methods:
            print("Naive encoding...")
            encoder_cmd = build_naive_encoder_cmd(target_dir, target_filename, out_filename, error_threshold)
            run_process(encoder_cmd)
            naive_size = get_file_size(os.path.join(Config.private_dir, out_filename))

            print("Naive decoding...")
            decoder_cmd = build_naive_decoder_cmd(out_filename)
            run_process(decoder_cmd)
            naive_points, _ = load_binary(os.path.join(Config.private_dir, target_filename))

            cr_naive = original_size / naive_size

            print("Computing naive metrics...")
            naive_to_original_mse, original_to_naive_mse = compute_p_cloud_mse(naive_points, target_points)

            print(f"Compression Ratio (Naive): {cr_naive}")
            print(f"MSE (Naive to Original): {naive_to_original_mse}")
            print(f"MSE (Original to Naive): {original_to_naive_mse}")

            current_df_row["naive_points_count"] = naive_points.shape[0]
            current_df_row["naive_size_bytes"] = naive_size
            current_df_row["naive_to_original_mse"] = naive_to_original_mse
            current_df_row["original_to_naive_mse"] = original_to_naive_mse

        if "accurate" in Config.methods:
            print("Accurate encoding...")
            encoder_cmd = build_accurate_encoder_cmd(target_dir, target_filename, intrinsics_file, out_filename,
                                                     error_threshold)
            run_process(encoder_cmd)
            accurate_size = get_file_size(os.path.join(Config.private_dir, out_filename))

            print("Accurate decoding...")
            decoder_cmd = build_accurate_decoder_cmd(out_filename, intrinsics_file)
            run_process(decoder_cmd)
            accurate_points, _ = load_binary(os.path.join(Config.private_dir, target_filename))

            cr_accurate = original_size / accurate_size

            print("Computing accurate metrics...")
            accurate_to_original_mse, original_to_accurate_mse = compute_p_cloud_mse(accurate_points, target_points)

            print(f"Compression Ratio (Accurate): {cr_accurate}")
            print(f"MSE (Accurate to Original): {accurate_to_original_mse}")
            print(f"MSE (Original to Accurate): {original_to_accurate_mse}")

            current_df_row["accurate_points_count"] = accurate_points.shape[0]
            current_df_row["accurate_size_bytes"] = accurate_size
            current_df_row["accurate_to_original_mse"] = accurate_to_original_mse
            current_df_row["original_to_accurate_mse"] = original_to_accurate_mse

        current_df_row["horizontal_step"] = Config.get_horizontal_step()
        current_df_row["vertical_step"] = Config.get_vertical_step()
        current_df_row["tile_size"] = Config.tile_size
        current_df_row["error_threshold"] = error_threshold
        current_df_row["original_points_count"] = target_points.shape[0]
        current_df_row["original_size_bytes"] = original_size

        df_rows.append(current_df_row)

    return pd.DataFrame(df_rows)


def evaluate(dataset, frame_path, intrinsics_filename, compression_out_filename):
    if Config.experiment_type == "ri":
        return evaluate_ri(dataset, frame_path, intrinsics_filename)
    elif Config.experiment_type == "compression":
        return evaluate_compression(dataset, frame_path, intrinsics_filename, compression_out_filename)
    else:
        raise ValueError(f"Unknown experiment type: {Config.experiment_type}")


def run_single(args):
    train_parts = args.train.split(":")
    target_parts = args.target.split(":")
    train_path = get_frame_path(args, train_parts[0], train_parts[1])
    target_path = get_frame_path(args, target_parts[0], target_parts[1])

    intrinsics_filename = "intrinsics.json"
    compression_out_filename = "out.tar.gz"

    train(train_path, intrinsics_filename)

    df = evaluate(target_parts[0], target_path, intrinsics_filename, compression_out_filename)

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
            derived_filename = relative_path.replace("/", "_")

            if args.phase == "train":
                intrinsics_filename = f"{derived_filename}.json"
                train(frame_path, intrinsics_filename)
            elif args.phase == "evaluate":
                corresponding_train_derived_filename = re.sub(r"\d{10}\.bin$", "0000000000.bin", derived_filename)
                intrinsics_filename = f"{corresponding_train_derived_filename}.json"
                compression_out_filename = f"{derived_filename}.tar.gz"

                df = evaluate(dataset, frame_path, intrinsics_filename, compression_out_filename)
                df["experiment_id"] = experiment_id
                df["dataset_frame_id"] = frame_id

                df.to_sql(Config.get_result_sql_table(), conn, if_exists="append", index=False)


def parse_args():
    parser = argparse.ArgumentParser(description="Compare naive and accurate point cloud compression.")
    parser.add_argument("--mode", required=True, choices=["batch", "single", "test"], help="Mode: batch or single.")
    parser.add_argument("--phase", default=None, choices=["train", "evaluate"], help="Execution phase (batch mode).")
    parser.add_argument("--type", default=None, choices=["ri", "compression"], help="What do with the range image, just project and unproject (ri) or compress (compress).")
    parser.add_argument("--task_id", type=int, default=None, help="Task ID (batch mode).")
    parser.add_argument("--task_count", type=int, default=None, help="Task count (batch mode).")
    parser.add_argument("--db_path", type=str, default=None, help="Path to the database file (batch mode).")
    parser.add_argument("--train", type=str, default=None, help="Train path (single mode).")
    parser.add_argument("--target", type=str, default=None, help="Target path (single mode).")
    parser.add_argument("--output_csv", type=str, default=None, help="Optional output CSV file (single mode).")
    parser.add_argument("--kitti_root", type=str, default=None, help="Path to KITTI dataset root directory (optional).")
    parser.add_argument("--durlar_root", type=str, default=None,
                        help="Path to DURLAR dataset root directory (optional).")
    parser.add_argument("--private_dir", type=str, default=None, help="Optional private directory for intermediate files.")
    parser.add_argument("--shared_dir", type=str, default=None, help="Optional shared directory for intermediate files.")
    parser.add_argument("--error_thresholds", type=float, nargs='+', default=None, help="List of error thresholds (overrides default).")
    parser.add_argument("--methods", type=str, nargs='+', default=None, help="List of methods to use (overrides default).")

    args = parser.parse_args()

    if args.mode == "test":
        return args

    Config.experiment_type = args.type

    if args.error_thresholds is not None:
        Config.error_thresholds = args.error_thresholds

    if args.methods is not None:
        Config.methods = args.methods

    if args.mode == "batch":
        if args.db_path is None or args.phase is None:
            parser.error("--db_path and --phase are required in batch mode.")
        if args.phase == "evaluate" and (args.task_id is None or args.task_count is None or args.type is None):
            parser.error("--type, --task_id and --task_count are required in batch mode when phase is 'evaluate'.")
        elif args.phase == "train":
            args.task_id = 0
            args.task_count = 1
    elif args.mode == "single":
        if args.train is None or args.target is None or args.output_csv is None or args.type is None:
            parser.error("--type, --train, --target, and --output_csv are required in single mode.")

        train_parts = args.train.split(":")
        target_parts = args.target.split(":")

        if len(train_parts) != 2 or train_parts[0] not in ["kitti", "durlar"]:
            parser.error("Invalid format for --train. Expected 'dataset:path'")

        if len(target_parts) != 2 or target_parts[0] not in ["kitti", "durlar"]:
            parser.error("Invalid format for --target. Expected 'dataset:path'")

    if not args.kitti_root and not args.durlar_root:
        parser.error("At least one of --kitti_root or --durlar_root must be defined.")

    if args.private_dir:
        Config.private_dir = args.private_dir

    if args.shared_dir:
        Config.shared_dir = args.shared_dir

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
