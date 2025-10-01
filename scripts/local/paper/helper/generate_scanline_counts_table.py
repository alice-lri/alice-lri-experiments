import os
import sqlite3

import pandas as pd

from scripts.common.helper.entities import *
from scripts.common.load_env import load_env
from scripts.local.paper.helper.utils import df_from_sql_table, compute_metrics

load_env()


def fetch_non_robust_frame_ids(conn, point_count_threshold=64) -> list[int]:
    scanline_gt_df = df_from_sql_table(conn, "dataset_frame_scanline_info_empirical")
    return scanline_gt_df[scanline_gt_df["points_count"] < point_count_threshold]["dataset_frame_id"].unique()


# TODO update tables to new schema
def fetch_full_dataset_frame_df(experiment_id: int) -> pd.DataFrame:
    conn = sqlite3.connect(os.getenv("LOCAL_SQLITE_MASTER_DB"))
    datasets_df = df_from_sql_table(conn, DatasetEntity.__table__)
    dataset_frames_df = df_from_sql_table(conn, DatasetFrame.__table__)
    frame_results_df = df_from_sql_table(conn, IntrinsicsFrameResult.__table__, "experiment_id == ?", (experiment_id,))
    # frame_gt_df = df_from_sql_table(conn, DatasetFrameGt.__table__)
    frame_gt_df = df_from_sql_table(conn, "dataset_frame_empirical")

    frame_full_df = pd.merge(dataset_frames_df, frame_results_df, left_on="id", right_on="dataset_frame_id", how="inner")
    frame_full_df = pd.merge(datasets_df, frame_full_df, left_on="id", right_on="dataset_id", how="inner")
    frame_full_df = pd.merge(frame_full_df, frame_gt_df, on="dataset_frame_id", how="inner", suffixes=("_estimated", "_gt"))

    non_robust_frame_ids = fetch_non_robust_frame_ids(conn)
    frame_full_df["robust"] = True
    frame_full_df.loc[frame_full_df["dataset_frame_id"].isin(non_robust_frame_ids), "robust"] = False

    return frame_full_df


def compute_scanline_metrics_df(frame_full_df: pd.DataFrame) -> pd.DataFrame:
    scanline_metrics_all_df = frame_full_df.groupby(["name"]) \
        .apply(lambda df: compute_metrics(df, "scanlines_count_gt", "scanlines_count_estimated"), include_groups=False) \
        .reset_index() \
        .assign(subset="All")

    scanline_metrics_robust_only_df = frame_full_df[frame_full_df["robust"]].groupby(["name"]) \
        .apply(lambda df: compute_metrics(df, "scanlines_count_gt", "scanlines_count_estimated"), include_groups=False) \
        .reset_index() \
        .assign(subset="n(l) >= 64")

    scanline_metrics_df = pd.concat([scanline_metrics_all_df, scanline_metrics_robust_only_df], axis=0)
    scanline_metrics_df = scanline_metrics_df.sort_values(by=["name", "subset"], ascending=[False, True])

    cols = scanline_metrics_df.columns.tolist()
    cols.insert(cols.index("name") + 1, cols.pop(cols.index("subset")))
    scanline_metrics_df = scanline_metrics_df[cols]

    return scanline_metrics_df


def main():
    print(f"Loading data from database at {os.getenv('LOCAL_SQLITE_MASTER_DB')}")
    frame_full_df = fetch_full_dataset_frame_df(38)

    print("Computing scanline metrics...")
    scanline_metrics_df = compute_scanline_metrics_df(frame_full_df)

    print(scanline_metrics_df)


if __name__ == "__main__":
    main()
