import os

from dotenv import load_dotenv
load_dotenv()

from ...common.helper.orm import *
from ...common.helper.entities import *

class OldScanlineGt(OrmEntity, table_name="dataset_frame_scanline_info_empirical"):
    dataset_frame_id: int
    scanline_idx: int
    laser_idx: int


def main():
    old_db = Database(os.getenv("OLD_SQLITE_DB"))
    db = Database(os.getenv("SQLITE_DB"))

    print("Fetching laser IDs...")
    dataset_laser_idx_to_laser_id: dict[tuple[int, int], int] = {}
    for laser_gt in DatasetLaserGt.all(db):
        dataset_laser_idx_to_laser_id[(laser_gt.dataset_id, laser_gt.laser_idx)] = laser_gt.id

    print("Fetching dataset frame IDs...")
    dataset_frame_id_to_dataset_id: dict[int, int] = {}
    for dataset_frame in DatasetFrame.all(db):
        dataset_frame_id_to_dataset_id[dataset_frame.id] = dataset_frame.dataset_id

    print("Computing new GT entries...")
    new_gts = []
    for old_gt in OldScanlineGt.all(old_db):
        dataset_id = dataset_frame_id_to_dataset_id[old_gt.dataset_frame_id]
        laser_id = dataset_laser_idx_to_laser_id[(dataset_id, old_gt.laser_idx)]
        gt = DatasetFrameScanlineGt(dataset_frame_id=old_gt.dataset_frame_id, laser_id=laser_id, scanline_idx=old_gt.scanline_idx)
        new_gts.append(gt)

    print("Saving...")
    DatasetFrameScanlineGt.save_all(db, new_gts)
    db.close()
    old_db.close()

if __name__ == "__main__":
    main()
