import os

import pandas as pd

from scripts.common.load_env import load_env
from scripts.local.paper.helper.common import fetch_main_experiment_id
from scripts.local.paper.helper.metrics import metrics_from_confusion_df
from scripts.local.paper.helper.utils import pd_read_sqlite_query, df_to_latex, write_paper_data, \
    df_format_dataset_names

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
        'mp': 'mP (\\%)',
        'mr': 'mR (\\%)',
        'mf1': 'mF1 (\\%)',
        'wp': 'wP (\\%)',
        'wr': 'wR (\\%)',
        'wf1': 'wF1 (\\%)',
        'oa': 'OA (\\%)'
    }

    OUTPUT_FILE = "scanline_count_metrics.tex"


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

    latex = df_to_latex(final_metrics_df, float_format="%.2f", column_format="ll" + "r" * (len(final_metrics_df.columns)))
    write_paper_data(latex, Config.OUTPUT_FILE)


def fetch_and_compute_confusion_matrix(experiment_id: int, robust_point_count_threshold=64) -> pd.DataFrame:
    query = """
            SELECT name AS dataset,
                   dfgt.dataset_frame_id NOT IN (
                       SELECT DISTINCT dataset_frame_id
                       FROM dataset_frame_scanline_gt
                       WHERE points_count < ?
                   ) AS robust,
                   dfgt.scanlines_count AS true, ifr.scanlines_count AS pred, COUNT(*) AS count
            FROM dataset d
                     INNER JOIN dataset_frame df ON d.id = df.dataset_id
                     INNER JOIN intrinsics_frame_result ifr ON df.id = ifr.dataset_frame_id
                     INNER JOIN dataset_frame_gt dfgt ON df.id = dfgt.dataset_frame_id
            WHERE experiment_id == ?
            GROUP BY name, robust, dfgt.scanlines_count, ifr.scanlines_count;
            """

    return pd_read_sqlite_query(Config.DB_PATH, query, params=(robust_point_count_threshold, experiment_id))


def format_final_table(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(by=["dataset", "subset"], ascending=[False, True])

    pd.set_option('display.max_columns', None)
    print(df)

    df["samples"] = df["samples"].map(lambda x: f"\\num{{{x}}}")
    df["incorrect"] = df["incorrect"].astype(str)
    df["subset"] = df["subset"].replace(Config.SUBSET_REPLACE)

    df = df.rename(columns=Config.COLUMNS_RENAME)
    df = df.set_index(["Dataset", "Subset"])
    df.columns = pd.MultiIndex.from_product([["\\textbf{Scanlines Count}"], list(df.columns)])
    df = df_format_dataset_names(df)

    return df


if __name__ == "__main__":
    main()