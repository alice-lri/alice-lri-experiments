import argparse
import os
import re
import shutil
import subprocess

from scripts.common.helper.orm import *
from scripts.common.helper.entities import *

class Constant:
    ARG_EXPERIMENTS = "experiments"
    ARG_COMPRESSION_EXPERIMENTS = "compression_experiments"
    ARG_RI_EXPERIMENTS = "ri_experiments"
    ARG_GROUND_TRUTH = "ground_truth"

    MERGE_TYPES = [ARG_EXPERIMENTS, ARG_RI_EXPERIMENTS, ARG_COMPRESSION_EXPERIMENTS, ARG_GROUND_TRUTH]


def main():
    args = parse_args()

    print("Backing up database...")
    backup_db(args.master_db_path)
    db_files = get_db_files(args.part_dbs_folder_path)

    if args.type == Constant.ARG_EXPERIMENTS:
        merge_experiment_databases(db_files, args.master_db_path, args.label, args.description)
    elif args.type == Constant.ARG_COMPRESSION_EXPERIMENTS:
        merge_compression_experiment_databases(db_files, args.master_db_path, args.label, args.description)
    elif args.type == Constant.ARG_RI_EXPERIMENTS:
        merge_ri_experiment_databases(db_files, args.master_db_path, args.label, args.description)
    elif args.type == Constant.ARG_GROUND_TRUTH:
        merge_ground_truth_databases(db_files, args.master_db_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge SQLite databases.")
    parser.add_argument("part_dbs_folder_path")
    parser.add_argument("master_db_path")
    parser.add_argument("--type", choices=Constant.MERGE_TYPES, required=True,
                        help=f"Type of databases to merge: {Constant.MERGE_TYPES}")
    parser.add_argument("--label")
    parser.add_argument("--description")
    args = parser.parse_args()

    if args.type != Constant.ARG_GROUND_TRUTH:
        if not args.label or not args.description:
            parser.error(f"--label and --description required when --type is '{Constant.ARG_EXPERIMENTS}'")

    return args

def backup_db(merged_db_path):
    base_backup_db_path = merged_db_path + '.bak'
    backup_db_path = base_backup_db_path

    if os.path.exists(base_backup_db_path):
        index = 1
        while os.path.exists(f'{base_backup_db_path}.{index}'):
            index += 1
        backup_db_path = f'{base_backup_db_path}.{index}'

    if os.path.exists(merged_db_path):
        shutil.copy(merged_db_path, backup_db_path)


def merge_experiment_databases(db_files, master_db_path, label, description):
    with Database(master_db_path) as master_db:
        with Database(db_files[0]) as first_db:
            experiment = IntrinsicsExperiment.one(first_db)

            experiment.label = label
            experiment.description = description
            experiment.commit_hash = get_commit_hash()
            experiment.timestamp = SQLExpr("DATETIME('now', 'localtime', 'subsec')")

            merged_experiment_id = experiment.save(master_db)

        files_count = len(db_files)
        for file_index, db_file in enumerate(db_files):
            print(f"Merging experiments database {file_index + 1}/{files_count}")

            with Database(db_file) as db:
                frame_results = IntrinsicsFrameResult.all(db)
                for frame_result in frame_results:
                    original_result_id = frame_result.id
                    frame_result.experiment_id = merged_experiment_id

                    frame_result.id = None
                    new_result_id = frame_result.save(master_db)

                    scanlines = IntrinsicsScanlineResult.where(db, "intrinsics_result_id = ?", (original_result_id,))

                    for scanline in scanlines:
                        scanline.id = None
                        scanline.intrinsics_result_id = new_result_id

                    IntrinsicsScanlineResult.save_all(master_db, scanlines)


def merge_compression_experiment_databases(db_files, master_db_path, label, description):
    merge_generic_experiment_databases(
        db_files, master_db_path, label, description, CompressionExperiment, CompressionFrameResult
    )


def merge_ri_experiment_databases(db_files, master_db_path, label, description):
    merge_generic_experiment_databases(
        db_files, master_db_path, label, description, RangeImageExperiment, RangeImageFrameResult
    )


def merge_generic_experiment_databases(
        db_files, master_db_path, label, description, experiment_type: type[OrmEntity], frame_type: type[OrmEntity]
):
    with Database(master_db_path) as master_db:
        experiment = experiment_type(
            label=label,
            description=description,
            commit_hash=get_commit_hash(),
            timestamp=SQLExpr("DATETIME('now', 'localtime', 'subsec')")
        )
        merged_experiment_id = experiment.save(master_db)

        files_count = len(db_files)
        for file_index, db_file in enumerate(db_files):
            print(f"Merging {experiment_type.__table__} database {file_index + 1}/{files_count}")

            with Database(db_file) as db:
                frames = frame_type.all(db)
                for frame in frames:
                    frame.id = None
                    frame.experiment_id = merged_experiment_id

                frame_type.save_all(master_db, frames)


def merge_ground_truth_databases(db_files, master_db_path):
    with Database(master_db_path) as master_db:
        files_count = len(db_files)

        for file_index, db_file in enumerate(db_files):
            print(f"Merging ground truth database {file_index + 1}/{files_count}")

            with Database(db_file) as db:
                frames = DatasetFrameGt.all(db)
                scanlines = DatasetFrameScanlineGt.all(db)

                for frame in frames:
                    frame.id = None

                for scanline in scanlines:
                    scanline.id = None

                DatasetFrameGt.save_all(master_db, frames)
                DatasetFrameScanlineGt.save_all(master_db, scanlines)


def get_db_files(folder_path):
    return [folder_path + "/" + f for f in os.listdir(folder_path) if re.fullmatch(r'\d+\.sqlite', f)]


def get_commit_hash() -> str | None:
    try:
        return subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('utf-8').strip()
    except subprocess.CalledProcessError:
        return None


if __name__ == "__main__":
    main()