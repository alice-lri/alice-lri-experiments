import os
import subprocess
import pandas as pd
import alice_lri

from common.helper.ri.ri_default_mapper import *

from common.load_env import load_env
load_env()

class Config:
    original_encoder_exec = os.getenv("RTST_ORIGINAL_ENCODER")
    original_decoder_exec = os.getenv("RTST_ORIGINAL_DECODER")
    modified_encoder_exec = os.getenv("RTST_MODIFIED_ENCODER")
    modified_decoder_exec = os.getenv("RTST_MODIFIED_DECODER")

    target_frames = [
        "2011_09_26/2011_09_26_drive_0001_sync/velodyne_points/data/0000000000.bin",
        "2011_09_26/2011_09_26_drive_0117_sync/velodyne_points/data/0000000000.bin",
        "2011_09_28/2011_09_28_drive_0001_sync/velodyne_points/data/0000000000.bin",
        "2011_09_28/2011_09_28_drive_0222_sync/velodyne_points/data/0000000000.bin",
        "2011_09_29/2011_09_29_drive_0004_sync/velodyne_points/data/0000000000.bin",
        "2011_09_29/2011_09_29_drive_0071_sync/velodyne_points/data/0000000000.bin",
        "2011_09_30/2011_09_30_drive_0016_sync/velodyne_points/data/0000000000.bin",
        "2011_09_30/2011_09_30_drive_0034_sync/velodyne_points/data/0000000000.bin",
        "2011_10_03/2011_10_03_drive_0027_sync/velodyne_points/data/0000000000.bin",
        "2011_10_03/2011_10_03_drive_0047_sync/velodyne_points/data/0000000000.bin",
    ]

    intrinsics_json = "intrinsics.json"
    output_csv = "rtst_times.csv"
    rtst_out_filename = "out.tar.gz"

    alice_lri_lib_path = os.getenv("ALICE_LRI_LIB_PATH")
    fmt = "binary"
    tile_size = "4"
    error_thresholds = [0.001, 0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 1]

    __kitti_horizontal_step = "0.09009"
    __kitti_vertical_step = "0.47"

    @staticmethod
    def get_horizontal_step():
        return Config.__kitti_horizontal_step

    @staticmethod
    def get_vertical_step():
        return Config.__kitti_vertical_step


class Globals:
    env = None


def run_process_capture_time(cmd):
    result = subprocess.run(cmd, check=True, env=Globals.env, capture_output=True, text=True)

    execution_time = None
    for line in result.stdout.split('\n'):
        if '[EXECUTION TIME (ms)]:' in line:
            execution_time = int(line.split(':')[-1].strip())
            break

    return execution_time


def get_frame_path(relative_path):
    frame_path = os.path.join(os.getenv("LOCAL_KITTI_PATH"), relative_path)
    return frame_path

#TODO extract to common
def build_naive_encoder_cmd(input_dir, input_file, output_file, error_threshold):
    return [
        os.path.abspath(Config.original_encoder_exec),
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
        os.path.abspath(Config.modified_encoder_exec),
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
        os.path.abspath(Config.original_decoder_exec),
        "-p", Config.get_horizontal_step(),
        "-y", Config.get_vertical_step(),
        "-f", Config.fmt,
        "-l", Config.tile_size,
        "--file", input_file
    ]


def build_accurate_decoder_cmd(input_file, intrinsics_file):
    return [
        os.path.abspath(Config.modified_decoder_exec),
        "-i", intrinsics_file,
        "-f", Config.fmt,
        "-l", Config.tile_size,
        "--file", input_file
    ]


def train(train_path):
    print("Loading train points from:", train_path)
    train_points, _ = load_binary(train_path)

    print("Training...")
    intrinsics = alice_lri.train(train_points[:, 0], train_points[:, 1], train_points[:, 2])

    intrinsics_file = os.path.abspath(Config.intrinsics_json)
    alice_lri.intrinsics_to_json_file(intrinsics, intrinsics_file)


def measure_times(target_path):
    target_dir = os.path.dirname(target_path)
    target_filename = os.path.basename(target_path)
    intrinsics_file = os.path.abspath(Config.intrinsics_json)
    df_rows = []

    print("Loading target points from:", target_path)
    for error_threshold in Config.error_thresholds:
        print(f"Error threshold: {error_threshold}")
        current_df_row = {}

        print("Naive encoding...")
        encoder_cmd = build_naive_encoder_cmd(target_dir, target_filename, Config.rtst_out_filename, error_threshold)
        current_df_row["naive_encoding_time"] = run_process_capture_time(encoder_cmd)

        print("Naive decoding...")
        decoder_cmd = build_naive_decoder_cmd(Config.rtst_out_filename)
        current_df_row["naive_decoding_time"] = run_process_capture_time(decoder_cmd)

        print("Accurate encoding...")
        encoder_cmd = build_accurate_encoder_cmd(target_dir, target_filename, intrinsics_file, Config.rtst_out_filename,
                                                 error_threshold)
        current_df_row["accurate_encoding_time"] = run_process_capture_time(encoder_cmd)

        print("Accurate decoding...")
        decoder_cmd = build_accurate_decoder_cmd(Config.rtst_out_filename, intrinsics_file)
        current_df_row["accurate_decoding_time"] = run_process_capture_time(decoder_cmd)

        current_df_row["horizontal_step"] = Config.get_horizontal_step()
        current_df_row["vertical_step"] = Config.get_vertical_step()
        current_df_row["tile_size"] = Config.tile_size
        current_df_row["error_threshold"] = error_threshold

        df_rows.append(current_df_row)

    return pd.DataFrame(df_rows)


def main():
    Globals.env = os.environ.copy()
    Globals.env["LD_LIBRARY_PATH"] = os.path.abspath(Config.alice_lri_lib_path)

    train(get_frame_path(Config.target_frames[0]))

    df = None
    for frame_path in Config.target_frames:
        print(f"Measuring times for frame: {frame_path}")
        current_df = measure_times(get_frame_path(frame_path))

        df = pd.concat([df, current_df], ignore_index=True) if df is not None else current_df

    df.to_csv(Config.output_csv, index=False)


if __name__ == "__main__":
    main()
