import argparse
import os
import sqlite3

import pandas as pd
import alice_lri

from scripts.common.load_env import load_env
from scripts.common.helper.local_geometry_experiment import (
    DEFAULT_METHODS,
    estimate_frame_relative_path,
    estimate_intrinsics,
    evaluate_frame_methods,
)
from scripts.common.helper.point_cloud import load_binary

load_env()


class Config:
    methods = DEFAULT_METHODS
    k_neighbors = 12


def parse_args():
    parser = argparse.ArgumentParser(description="Run local point-to-plane geometry metrics on SLURM.")
    parser.add_argument("--mode", required=True, choices=["batch", "test"], help="Execution mode.")
    parser.add_argument("--phase", default=None, choices=["estimate", "evaluate"], help="Execution phase in batch mode.")
    parser.add_argument("--task_id", type=int, default=None, help="Task ID in batch mode.")
    parser.add_argument("--task_count", type=int, default=None, help="Task count in batch mode.")
    parser.add_argument("--db_path", type=str, default=None, help="Task-local SQLite database.")
    parser.add_argument("--kitti_root", type=str, default=None, help="KITTI dataset root.")
    parser.add_argument("--durlar_root", type=str, default=None, help="DurLAR dataset root.")
    parser.add_argument("--shared_dir", type=str, default=None, help="Shared directory for estimated intrinsics JSONs.")
    parser.add_argument("--k_neighbors", type=int, default=Config.k_neighbors, help="PCA neighborhood size.")

    args = parser.parse_args()

    if args.mode == "test":
        return args

    if args.phase is None or args.db_path is None or args.shared_dir is None:
        parser.error("--phase, --db_path, and --shared_dir are required in batch mode.")

    if args.phase == "estimate":
        args.task_id = 0
        args.task_count = 1
    elif args.task_id is None or args.task_count is None:
        parser.error("--task_id and --task_count are required in batch evaluate phase.")

    if not args.kitti_root and not args.durlar_root:
        parser.error("At least one of --kitti_root or --durlar_root must be defined.")

    Config.k_neighbors = args.k_neighbors

    return args


def main():
    args = parse_args()

    if args.mode == "test":
        print("If you see no errors, all is good.")
        return

    os.makedirs(args.shared_dir, exist_ok=True)
    if args.phase == "estimate":
        run_estimate(args)
    elif args.phase == "evaluate":
        run_evaluate(args)
    else:
        raise ValueError(f"Unknown phase: {args.phase}")


def run_estimate(args):
    dataset_roots = {}
    if args.kitti_root:
        dataset_roots["kitti"] = args.kitti_root
    if args.durlar_root:
        dataset_roots["durlar"] = args.durlar_root

    with sqlite3.connect(f"file:{args.db_path}?mode=ro", uri=True) as conn:
        frames = fetch_estimation_frames(conn, dataset_roots.keys())
        print(f"Number of estimation frames: {len(frames)}")

        for _, dataset, relative_path in frames:
            intrinsics_filename = intrinsics_filename_from_relative_path(relative_path)
            intrinsics_path = os.path.join(args.shared_dir, intrinsics_filename)

            if os.path.exists(intrinsics_path):
                print(f"Skipping existing intrinsics file: {intrinsics_path}")
                continue

            frame_path = os.path.join(dataset_roots[dataset], relative_path)
            print(f"Estimating intrinsics from {dataset}:{relative_path}")
            estimate_points, _ = load_binary(frame_path)
            intrinsics = estimate_intrinsics(alice_lri, estimate_points)
            alice_lri.intrinsics_to_json_file(intrinsics, intrinsics_path)


def run_evaluate(args):
    dataset_roots = {}
    if args.kitti_root:
        dataset_roots["kitti"] = args.kitti_root
    if args.durlar_root:
        dataset_roots["durlar"] = args.durlar_root

    with sqlite3.connect(args.db_path) as conn:
        assert_schema(conn)
        experiment_id = fetch_experiment_id(conn)
        frames = fetch_task_frames(conn, dataset_roots.keys(), args.task_id, args.task_count)
        print(f"Number of frames: {len(frames)}")

        intrinsics_cache = {}
        for frame_id, dataset, relative_path in frames:
            print(f"Evaluating frame {frame_id}: {dataset}:{relative_path}")
            frame_path = os.path.join(dataset_roots[dataset], relative_path)
            original_points, _ = load_binary(frame_path)

            estimate_relative_path = estimate_frame_relative_path(relative_path)
            intrinsics_key = (dataset, estimate_relative_path)

            if "alice_lri" in Config.methods and intrinsics_key not in intrinsics_cache:
                intrinsics_path = os.path.join(args.shared_dir, intrinsics_filename_from_relative_path(estimate_relative_path))
                print(f"Loading intrinsics from {intrinsics_path}")
                intrinsics_cache[intrinsics_key] = alice_lri.intrinsics_from_json_file(intrinsics_path)

            rows = evaluate_frame_methods(
                alice_lri_module=alice_lri,
                dataset=dataset,
                original_points=original_points,
                intrinsics=intrinsics_cache.get(intrinsics_key),
                methods=Config.methods,
                k_neighbors=Config.k_neighbors,
                base_fields={
                    "experiment_id": experiment_id,
                    "dataset_frame_id": frame_id,
                },
            )

            pd.DataFrame(rows).to_sql("local_geometry_frame_result", conn, if_exists="append", index=False)
            conn.commit()


def assert_schema(conn: sqlite3.Connection):
    required_tables = {"local_geometry_experiment", "local_geometry_frame_result"}
    existing_tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    }
    missing_tables = required_tables - existing_tables
    if missing_tables:
        raise RuntimeError(
            "Missing local-geometry tables in the task database: "
            f"{sorted(missing_tables)}. Apply scripts/local/db/sql/001_local_geometry_experiment.sql "
            "to the initial/master databases before launching or merging this experiment."
        )


def fetch_experiment_id(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT MAX(id) FROM local_geometry_experiment").fetchone()
    experiment_id = row[0]
    assert experiment_id is not None, "Experiment ID must be defined."

    return experiment_id


def fetch_task_frames(conn: sqlite3.Connection, dataset_names, task_id: int, task_count: int):
    dataset_names = list(dataset_names)
    placeholders = ",".join(["?"] * len(dataset_names))
    query = f"""
        SELECT df.id, d.name, df.relative_path
        FROM dataset_frame AS df
        JOIN dataset AS d ON d.id = df.dataset_id
        WHERE df.id % ? == ?
          AND d.name IN ({placeholders})
        ORDER BY df.id
    """

    return conn.execute(query, (task_count, task_id, *dataset_names)).fetchall()


def fetch_estimation_frames(conn: sqlite3.Connection, dataset_names):
    dataset_names = list(dataset_names)
    placeholders = ",".join(["?"] * len(dataset_names))
    query = f"""
        SELECT df.id, d.name, df.relative_path
        FROM dataset_frame AS df
        JOIN dataset AS d ON d.id = df.dataset_id
        WHERE d.name IN ({placeholders})
          AND df.relative_path LIKE ?
        ORDER BY df.id
    """

    return conn.execute(query, (*dataset_names, "%0000000000.bin")).fetchall()


def intrinsics_filename_from_relative_path(relative_path: str) -> str:
    return relative_path.replace("/", "_") + ".json"


if __name__ == "__main__":
    main()
