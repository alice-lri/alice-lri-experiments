import os

import pandas as pd

from scripts.common.load_env import load_env
from scripts.local.paper.helper.common import fetch_main_experiment_id
from scripts.local.paper.helper.metrics import metrics_from_confusion_df
from scripts.local.paper.helper.utils import pd_read_sqlite_query

load_env()

class Config:
    DB_PATH = os.getenv("LOCAL_SQLITE_MASTER_DB")


def main():
    print(f"Using database at {Config.DB_PATH}")
    experiment_id = fetch_main_experiment_id(Config.DB_PATH)
    print(f"Experiment ID: {experiment_id}")

    print("Computing confusion matrices from DB. This may take a while...")
    confusion_matrix_all_df = fetch_and_compute_confusion_matrix(experiment_id)
    confusion_matrix_robust_only = confusion_matrix_all_df[confusion_matrix_all_df["robust"] == True]

    print("Computing metrics...")
    all_metrics_df = metrics_from_confusion_df(confusion_matrix_all_df, group_cols=["dataset"]).assign(subset="all")
    robust_only_metrics_df = metrics_from_confusion_df(confusion_matrix_robust_only, group_cols=["dataset"]).assign(subset="robust_only")
    final_metrics_df = pd.concat([all_metrics_df, robust_only_metrics_df])

    print(format_final_table(final_metrics_df))


# TODO update tables to new schema
def fetch_and_compute_confusion_matrix(experiment_id: int, robust_point_count_threshold=64) -> pd.DataFrame:
    query = """
         SELECT name AS dataset,
                dfsie.dataset_frame_id NOT IN (
                    SELECT DISTINCT dataset_frame_id
                    FROM dataset_frame_scanline_info_empirical
                    WHERE points_count < ?
                ) AS robust,
                dfsie.horizontal_resolution AS true,
                COALESCE(irsi.horizontal_resolution, -1) AS pred,
                COUNT(*) AS count
         FROM dataset d
                  INNER JOIN dataset_frame df ON df.dataset_id = d.id
                  INNER JOIN intrinsics_frame_result ifr ON ifr.dataset_frame_id = df.id
                  INNER JOIN dataset_frame_scanline_info_empirical dfsie ON dfsie.dataset_frame_id = df.id
                  LEFT JOIN intrinsics_result_scanline_info irsi ON irsi.intrinsics_result_id = ifr.id
                    AND irsi.scanline_idx = dfsie.scanline_idx
         WHERE experiment_id = ?
         GROUP BY name, robust, dfsie.horizontal_resolution, irsi.horizontal_resolution
    """

    return pd_read_sqlite_query(Config.DB_PATH, query, params=(robust_point_count_threshold, experiment_id))


# TODO complete formatting
def format_final_table(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(by=["dataset", "subset"], ascending=[False, True])
    df = df[["dataset", "subset", "samples", "incorrect", "oa"]]

    return df


if __name__ == "__main__":
    main()
