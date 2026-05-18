import argparse
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import alice_lri

from scripts.common.load_env import load_env
from scripts.common.helper.local_geometry_metrics import symmetric_point_to_plane_metrics
from scripts.common.helper.point_cloud import load_binary
from scripts.common.helper.ri.ri_default_mapper import RangeImageDefaultMapper
from scripts.common.helper.ri.ri_utils import point_cloud_to_range_image, range_image_to_point_cloud


class Config:
    default_sequences = {
        "kitti": "2011_09_30_drive_0018_sync",
        "durlar": "DurLAR_20211209",
    }
    pbea_native_resolutions = {
        "kitti": (4000, 64),
        "durlar": (2048, 128),
    }


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run local point-to-plane geometry checks for the R2.7 revision experiment."
    )
    parser.add_argument(
        "--db_path",
        default=None,
        help="Read-only SQLite DB used only to select frames. Defaults to LOCAL_SQLITE_MASTER_DB.",
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        choices=["kitti", "durlar"],
        default=["kitti", "durlar"],
        help="Datasets to evaluate when selecting frames from the DB.",
    )
    parser.add_argument(
        "--max_frames_per_dataset",
        type=int,
        default=1,
        help="Number of frames per dataset for the local subset.",
    )
    parser.add_argument(
        "--frame",
        action="append",
        default=None,
        help="Explicit frame in the form dataset:relative/path.bin. Can be repeated; bypasses DB selection.",
    )
    parser.add_argument("--kitti_root", default=None, help="KITTI root. Defaults to LOCAL_KITTI_PATH.")
    parser.add_argument("--durlar_root", default=None, help="DurLAR root. Defaults to LOCAL_DURLAR_PATH.")
    parser.add_argument("--k_neighbors", type=int, default=12, help="PCA neighborhood size.")
    parser.add_argument(
        "--methods",
        nargs="+",
        choices=["alice_lri", "pbea_native"],
        default=["alice_lri", "pbea_native"],
        help="Methods to evaluate.",
    )
    parser.add_argument(
        "--output_csv",
        default=None,
        help="Output CSV path. Defaults to results/local_geometry/local_geometry_metrics.csv.",
    )
    parser.add_argument(
        "--output_sqlite",
        default=None,
        help="Optional derived SQLite output. Defaults to results/local_geometry/local_geometry_metrics.sqlite.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output CSV/SQLite files.",
    )

    return parser.parse_args()


def main():
    project_root = load_env()
    args = parse_args()

    output_csv = Path(args.output_csv or project_root / "results/local_geometry/local_geometry_metrics.csv")
    output_sqlite = Path(args.output_sqlite or project_root / "results/local_geometry/local_geometry_metrics.sqlite")
    _prepare_output_path(output_csv, args.overwrite)
    _prepare_output_path(output_sqlite, args.overwrite)

    frame_specs = parse_explicit_frames(args.frame) if args.frame else select_frames(args)
    if not frame_specs:
        raise RuntimeError("No frames selected for the local geometry experiment.")

    dataset_roots = {
        "kitti": Path(args.kitti_root or os.getenv("LOCAL_KITTI_PATH", "")),
        "durlar": Path(args.durlar_root or os.getenv("LOCAL_DURLAR_PATH", "")),
    }

    intrinsics_cache = {}
    rows = []
    for dataset, relative_path, dataset_frame_id in frame_specs:
        frame_path = dataset_roots[dataset] / relative_path
        if not frame_path.exists():
            raise FileNotFoundError(f"Frame not found: {frame_path}")

        print(f"Loading {dataset}:{relative_path}")
        original_points, _ = load_binary(frame_path)
        estimate_relative_path = estimate_frame_relative_path(relative_path)
        intrinsics_key = (dataset, estimate_relative_path)

        if "alice_lri" in args.methods and intrinsics_key not in intrinsics_cache:
            estimate_path = dataset_roots[dataset] / estimate_relative_path
            if not estimate_path.exists():
                raise FileNotFoundError(f"Intrinsics-estimation frame not found: {estimate_path}")

            print(f"Estimating ALICE-LRI intrinsics from {dataset}:{estimate_relative_path}")
            estimate_points, _ = load_binary(estimate_path)
            intrinsics_cache[intrinsics_key] = alice_lri.estimate_intrinsics(
                estimate_points[:, 0], estimate_points[:, 1], estimate_points[:, 2]
            )

        if "alice_lri" in args.methods:
            print("Evaluating ALICE-LRI...")
            start_time = time.perf_counter()
            reconstructed_points, ri_width, ri_height = reconstruct_alice_lri(
                alice_lri, intrinsics_cache[intrinsics_key], original_points
            )
            rows.append(
                build_metrics_row(
                    dataset=dataset,
                    dataset_frame_id=dataset_frame_id,
                    relative_path=relative_path,
                    estimate_relative_path=estimate_relative_path,
                    method="alice_lri",
                    ri_width=ri_width,
                    ri_height=ri_height,
                    original_points=original_points,
                    reconstructed_points=reconstructed_points,
                    k_neighbors=args.k_neighbors,
                    runtime_seconds=time.perf_counter() - start_time,
                )
            )

        if "pbea_native" in args.methods:
            print("Evaluating native-resolution PBEA...")
            start_time = time.perf_counter()
            reconstructed_points, ri_width, ri_height = reconstruct_pbea_native(dataset, original_points)
            rows.append(
                build_metrics_row(
                    dataset=dataset,
                    dataset_frame_id=dataset_frame_id,
                    relative_path=relative_path,
                    estimate_relative_path=estimate_relative_path,
                    method="pbea_native",
                    ri_width=ri_width,
                    ri_height=ri_height,
                    original_points=original_points,
                    reconstructed_points=reconstructed_points,
                    k_neighbors=args.k_neighbors,
                    runtime_seconds=time.perf_counter() - start_time,
                )
            )

    results = pd.DataFrame(rows)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(output_csv, index=False)
    print(f"Wrote CSV results to {output_csv}")

    output_sqlite.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(output_sqlite) as conn:
        results.to_sql("local_geometry_frame_result", conn, if_exists="append", index=False)
    print(f"Wrote SQLite results to {output_sqlite}")

    print("\nAggregate point-to-plane metrics:")
    print(
        results.groupby(["dataset", "method"])[
            ["point_to_plane_mean", "point_to_plane_rmse", "point_to_plane_p95"]
        ].mean()
    )


def parse_explicit_frames(frame_args: list[str]) -> list[tuple[str, str, int | None]]:
    frames = []
    for frame_arg in frame_args:
        parts = frame_arg.split(":", 1)
        if len(parts) != 2 or parts[0] not in Config.default_sequences:
            raise ValueError(f"Invalid --frame value: {frame_arg}. Expected dataset:relative/path.bin")
        frames.append((parts[0], parts[1], None))
    return frames


def select_frames(args) -> list[tuple[str, str, int | None]]:
    db_path = args.db_path or os.getenv("LOCAL_SQLITE_INITIAL_DB")
    if not db_path or not Path(db_path).exists():
        raise FileNotFoundError(
            "Frame selection requires a readable DB. Pass --db_path or use explicit --frame values."
        )

    frames = []
    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
        for dataset in args.datasets:
            sequence = Config.default_sequences[dataset]
            query = """
                SELECT d.name, df.relative_path, df.id
                FROM dataset_frame AS df
                JOIN dataset AS d ON d.id = df.dataset_id
                WHERE d.name = ? AND df.relative_path LIKE ?
                ORDER BY df.relative_path
                LIMIT ?
            """
            frames.extend(
                conn.execute(query, (dataset, f"%{sequence}%", args.max_frames_per_dataset)).fetchall()
            )

    return frames


def estimate_frame_relative_path(relative_path: str) -> str:
    estimate_path = re.sub(r"\d{10}\.bin$", "0000000000.bin", relative_path)
    if estimate_path == relative_path and not relative_path.endswith("0000000000.bin"):
        raise ValueError(f"Could not infer intrinsics-estimation frame from path: {relative_path}")
    return estimate_path


def reconstruct_alice_lri(alice_lri, intrinsics, original_points):
    range_image = alice_lri.project_to_range_image(
        intrinsics,
        original_points[:, 0],
        original_points[:, 1],
        original_points[:, 2],
    )
    x, y, z = alice_lri.unproject_to_point_cloud(intrinsics, range_image)

    return np.column_stack((x, y, z)), range_image.width, range_image.height


def reconstruct_pbea_native(dataset: str, original_points):
    ri_width, ri_height = Config.pbea_native_resolutions[dataset]
    ri_mapper = RangeImageDefaultMapper(ri_width, ri_height)
    range_image = point_cloud_to_range_image(ri_mapper, original_points)
    reconstructed_points = range_image_to_point_cloud(ri_mapper, range_image)

    return reconstructed_points, ri_width, ri_height


def build_metrics_row(
    dataset: str,
    dataset_frame_id: int | None,
    relative_path: str,
    estimate_relative_path: str,
    method: str,
    ri_width: int,
    ri_height: int,
    original_points,
    reconstructed_points,
    k_neighbors: int,
    runtime_seconds: float,
) -> dict:
    metrics_start_time = time.perf_counter()
    metrics = symmetric_point_to_plane_metrics(original_points, reconstructed_points, k_neighbors)
    metrics_runtime_seconds = time.perf_counter() - metrics_start_time

    return {
        "dataset": dataset,
        "dataset_frame_id": dataset_frame_id,
        "relative_path": relative_path,
        "estimate_relative_path": estimate_relative_path,
        "method": method,
        "ri_width": ri_width,
        "ri_height": ri_height,
        "original_points_count": len(original_points),
        "reconstructed_points_count": len(reconstructed_points),
        "k_neighbors": k_neighbors,
        "runtime_seconds": runtime_seconds + metrics_runtime_seconds,
        "metrics_runtime_seconds": metrics_runtime_seconds,
        **metrics,
    }


def _prepare_output_path(path: Path, overwrite: bool):
    if path.exists() and overwrite:
        path.unlink()
    elif path.exists() and not overwrite:
        raise FileExistsError(f"Output already exists: {path}. Use --overwrite to replace it.")


if __name__ == "__main__":
    main()
