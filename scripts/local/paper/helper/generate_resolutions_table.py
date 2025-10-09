import os

import numpy as np
import pandas as pd

from scripts.common.load_env import load_env
from scripts.local.paper.helper.common import fetch_main_experiment_id
from scripts.local.paper.helper.metrics import metrics_from_confusion_df
from scripts.local.paper.helper.utils import pd_read_sqlite_query, df_format_dataset_names, df_to_latex, \
    write_paper_data

load_env()

class Config:
    DB_PATH = os.getenv("LOCAL_SQLITE_MASTER_DB")
    ROBUST_POINT_COUNT_THRESHOLD = 64

    SUBSET_REPLACE = {
        "all": "All",
        "robust_only": f"$n^{{(l)}} \\geq {ROBUST_POINT_COUNT_THRESHOLD}$"
    }
    COLUMNS_RENAME = {
        'dataset': 'Dataset',
        'subset': 'Subset',
        'samples': '\\# Samples',
        'incorrect': '\\# Incorrect',
        'oa': 'OA (\\%)'
    }

    OUTPUT_FILE = "resolution_metrics.tex"


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
    final_metrics_df = format_final_table(final_metrics_df)

    latex = df_to_latex(final_metrics_df, float_format="%.2f", column_format="llrrr")
    write_paper_data(latex, Config.OUTPUT_FILE)


def fetch_and_compute_confusion_matrix(experiment_id: int, robust_point_count_threshold=64) -> pd.DataFrame:
    query = """
         SELECT name AS dataset,
                scanline_gt.dataset_frame_id NOT IN (
                    SELECT DISTINCT dataset_frame_id
                    FROM dataset_frame_scanline_gt
                    WHERE points_count < ?
                ) AS robust,
                laser_gt.horizontal_resolution AS true,
                COALESCE(scanline.horizontal_resolution, -1) AS pred,
                COUNT(*) AS count
         FROM dataset d
                  INNER JOIN dataset_frame df ON df.dataset_id = d.id
                  INNER JOIN intrinsics_frame_result ifr ON ifr.dataset_frame_id = df.id
                  INNER JOIN dataset_frame_scanline_gt scanline_gt ON scanline_gt.dataset_frame_id = df.id
                  INNER JOIN dataset_laser_gt laser_gt ON laser_gt.id = scanline_gt.laser_id
                  LEFT JOIN intrinsics_scanline_result scanline ON scanline.intrinsics_result_id = ifr.id
                    AND scanline.scanline_idx = scanline_gt.scanline_idx
         WHERE experiment_id = ?
         GROUP BY name, robust, laser_gt.horizontal_resolution, scanline.horizontal_resolution
    """

    return pd_read_sqlite_query(Config.DB_PATH, query, params=(robust_point_count_threshold, experiment_id))


def format_final_table(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(by=["dataset", "subset"], ascending=[False, True])
    df = df[["dataset", "subset", "samples", "incorrect", "oa"]]
    print(df)

    df["samples"] = df["samples"].map(lambda x: f"\\num{{{x}}}")
    df["incorrect"] = df["incorrect"].astype(str)
    df["subset"] = df["subset"].replace(Config.SUBSET_REPLACE)
    # show 99.99 instead of 100.00 unless it's exactly 100
    df["oa"] = df["oa"].map(lambda x: np.floor(x * 100) / 100)
    df = df.rename(columns=Config.COLUMNS_RENAME)
    df = df.set_index(["Dataset", "Subset"])
    df.columns = pd.MultiIndex.from_product([["\\textbf{Horizontal Resolution}"], list(df.columns)])
    df = df_format_dataset_names(df)

    return df


if __name__ == "__main__":
    main()
