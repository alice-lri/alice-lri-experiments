import os
import glob
import random
import subprocess
import numpy as np
import pandas as pd
import open3d as o3d
import shutil

CONFIG = {
    "naive_encoder_exec": "build/pcc_encoder",
    "accurate_encoder_exec": "build/pcc_encoder_accurate",
    "naive_decoder_exec": "build/pcc_decoder",
    "accurate_decoder_exec": "build/pcc_decoder_accurate",
    "horizontal_step": "0.09",
    "vertical_step": "0.45",
    "fmt": "binary",
    "tile_size": "4",
    "error_threshold": [0.001, 0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 1],
    "out_path": "data",
    "out_file_naive": "frame_naive.tar.gz",
    "out_file_accurate": "frame_accurate.tar.gz",
    "cwd": "../",
    "n_samples": 500,
    "results_file": "results.csv"
}

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


def run_process(cmd, cwd):
    subprocess.run(cmd, check=True, cwd=cwd)


def get_file_size(path):
    return os.path.getsize(path)


def create_output_path(decoded_path):
    os.makedirs(os.path.dirname(decoded_path), exist_ok=True)


def build_encoder_cmd(exec_path, input_file, output_file, config, error_threshold):
    rel_input = input_file.replace("../data/", "")
    return [
        exec_path,
        "--file", rel_input,
        "--path", config["out_path"],
        "-p", config["horizontal_step"],
        "-y", config["vertical_step"],
        "-f", config["fmt"],
        "-l", config["tile_size"],
        "-t", str(error_threshold),
        "--out", output_file
    ]


def build_decoder_cmd(exec_path, output_file, config):
    return [
        exec_path,
        "-p", config["horizontal_step"],
        "-y", config["vertical_step"],
        "-f", config["fmt"],
        "-l", config["tile_size"],
        "--file", output_file
    ]


def main():
    bin_files = glob.glob("../data/raw/*/*/velodyne_points/data/*.bin")
    random.seed(17)
    bin_files = random.sample(bin_files, CONFIG["n_samples"])

    results = []

    for input_file in bin_files:
        for error_threshold in CONFIG["error_threshold"]:
            # Encoding
            naive_cmd = build_encoder_cmd(CONFIG["naive_encoder_exec"], input_file, 
                                          CONFIG["out_file_naive"], CONFIG, error_threshold)
            accurate_cmd = build_encoder_cmd(CONFIG["accurate_encoder_exec"], input_file, 
                                             CONFIG["out_file_accurate"], CONFIG, error_threshold)
            run_process(naive_cmd, CONFIG["cwd"])
            run_process(accurate_cmd, CONFIG["cwd"])

            # File sizes
            original_size = get_file_size(input_file)
            naive_size = get_file_size(f"../{CONFIG['out_file_naive']}")
            accurate_size = get_file_size(f"../{CONFIG['out_file_accurate']}")

            print(f"Original size: {original_size / 1024:.2f} KB")
            print(f"Naive encoded size: {naive_size / 1024:.2f} KB")
            print(f"Accurate encoded size: {accurate_size / 1024:.2f} KB")

            # Decoding and Chamfer Distance for Naive
            decoded_path = input_file.replace("../data/raw/", "../raw/")
            create_output_path(decoded_path)

            naive_decode_cmd = build_decoder_cmd(CONFIG["naive_decoder_exec"], CONFIG["out_file_naive"], CONFIG)
            run_process(naive_decode_cmd, CONFIG["cwd"])
            naive_target_path = decoded_path.replace("../raw/", "../raw/naive/")
            create_output_path(naive_target_path)
            shutil.move(decoded_path, naive_target_path)

            accurate_decode_cmd = build_decoder_cmd(CONFIG["accurate_decoder_exec"], CONFIG["out_file_accurate"], CONFIG)
            run_process(accurate_decode_cmd, CONFIG["cwd"])
            accurate_target_path = decoded_path.replace("../raw/", "../raw/accurate/")
            create_output_path(accurate_target_path)
            shutil.move(decoded_path, accurate_target_path)


            pc_original, _ = load_binary(input_file)
            pc_naive, _ = load_binary(naive_target_path)
            cd_naive, _, _ = chamfer_distance(pc_original, pc_naive)

            pc_accurate, _ = load_binary(accurate_target_path)
            cd_accurate, _, _ = chamfer_distance(pc_original, pc_accurate)

            print(f"Chamfer distance (Naive): {cd_naive:.6f}")
            print(f"Chamfer distance (Accurate): {cd_accurate:.6f}")

            results.append({
                "input_file": input_file,
                "original_size": original_size,
                "naive_size": naive_size,
                "accurate_size": accurate_size,
                "cd_naive": cd_naive,
                "cd_accurate": cd_accurate,
                "horizontal_step": CONFIG["horizontal_step"],
                "vertical_step": CONFIG["vertical_step"],
                "tile_size": CONFIG["tile_size"],
                "error_threshold": error_threshold
            })

            df = pd.DataFrame(results)
            df.to_csv(CONFIG["results_file"], index=False)

if __name__ == "__main__":
    main()
