import argparse
import os

from scripts.common.helper.orm import Database
from ...common.helper.datasets.durlar import *
from ...common.helper.datasets.kitti import *
from ...common.helper.entities import *
from ...common.helper.ground_truth import *


class Config:
    datasets: dict[str, tuple[Dataset, str]] = {
        "kitti": (KITTI(), os.getenv("KITTI_PATH")),
        "durlar": (DurLAR(), os.getenv("DURLAR_PATH")),
    }


class Args:
    db_path: str
    process_id: int
    total_processes: int


def main():
    parse_args()
    with Database(Args.db_path) as db:
        datasets = DatasetEntity.all(db)
        dataset_id_to_name = {dataset.id: dataset.name for dataset in datasets}

        frames = DatasetFrame.where(db, "id % ? = ?", (Args.total_processes, Args.process_id))
        print(f"Process {Args.process_id}/{Args.total_processes} - Assigned {len(frames)} frames")

        all_gt_entities = []
        for i, frame in enumerate(frames):
            print(f"Processing {frame['relative_path']}")

            gr_result = compute_ground_truth_from_frame(frame, dataset_id_to_name)
            gt_entities = build_scanline_gt_entities(frame.id, gr_result)
            all_gt_entities.extend(gt_entities)

            print(f"Process {Args.process_id}/{Args.total_processes} - Processed {i + 1}/{len(frames)} frames")

        print(f"Process {Args.process_id}/{Args.total_processes} - Saving...")
        DatasetFrameScanlineGt.save_all(db, all_gt_entities)
        print(f"Process {Args.process_id}/{Args.total_processes} - Finished all {len(frames)} frames successfully")


def parse_args():
    parser = argparse.ArgumentParser(description='Populate ground truth database in parallel.')
    parser.add_argument('process_id', type=int, help='ID of the current process (0-indexed)')
    parser.add_argument('total_processes', type=int, help='Total number of processes')
    parser.add_argument('--db_path', type=str, required=True, help='Path to the SQLite database')
    args = parser.parse_args()

    assert os.path.exists(args.db_path), f"Database path does not exist: {args.db_path}"

    Args.db_path = args.db_path
    Args.process_id = args.process_id
    Args.total_processes = args.total_processes


def compute_ground_truth_from_frame(frame: DatasetFrame, dataset_id_to_name: dict[int, str]):
    dataset_name = dataset_id_to_name[frame.dataset_id]
    dataset_data, base_path = Config.datasets[dataset_name]
    points, _ = load_binary(os.path.join(base_path, frame.relative_path))
    points = points[calculate_range(points) > 0]

    _, gt_result = compute_ground_truth(
        points, dataset_data.v_angles, dataset_data.v_offsets, dataset_data.h_offsets, dataset_data.h_resolutions
    )

    return gt_result


def build_scanline_gt_entities(dataset_frame_id: int, gt_result: dict):
    result = []
    for scanline_idx, s in enumerate(gt_result["scanlines"]):
        scanline_gt = DatasetFrameScanlineGt(
            dataset_frame_id=dataset_frame_id,
            laser_id=s["laser_idx"],
            scanline_idx=scanline_idx,
        )
        result.append(scanline_gt)

    return result


if __name__ == "__main__":
    main()
