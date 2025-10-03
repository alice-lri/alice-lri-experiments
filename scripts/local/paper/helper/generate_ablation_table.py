import os

import pandas as pd

from scripts.common.load_env import load_env
from scripts.local.paper.helper.utils import pd_read_sqlite_query

load_env()

class Config:
    DB_PATH = os.getenv("LOCAL_SQLITE_MASTER_DB")


def main():
    print(f"Using database at {Config.DB_PATH}")

    print("Computing scanline ablation results from DB. This may take a while...")
    scanline_ablation_final_df = generate_scanline_ablation_df()

    pd.set_option('display.max_columns', None)
    print(scanline_ablation_final_df)


def generate_scanline_ablation_df() -> pd.DataFrame:
    scanline_ablation_all_df = fetch_and_compute_scanline_ablation()
    scanline_ablation_robust_only_df = scanline_ablation_all_df[scanline_ablation_all_df["robust"] == True]

    all_cols = set(scanline_ablation_all_df.columns.tolist())
    group_cols = list(all_cols - {"robust", "incorrect_count"})
    scanline_ablation_all_df = scanline_ablation_all_df\
        .groupby(group_cols).agg({"incorrect_count": "sum"}).reset_index()
    scanline_ablation_robust_only_df = scanline_ablation_robust_only_df\
        .groupby(group_cols).agg({"incorrect_count": "sum"}).reset_index()

    scanline_ablation_all_df = format_to_experiment_configuration(scanline_ablation_all_df, False)
    scanline_ablation_robust_only_df = format_to_experiment_configuration(scanline_ablation_robust_only_df, True)

    merge_cols = list(set(scanline_ablation_all_df.columns) - {"incorrect_count_robust_only", "incorrect_count"})
    scanline_ablation_final_df = scanline_ablation_all_df.merge(scanline_ablation_robust_only_df, on=merge_cols)
    return scanline_ablation_final_df


# TODO update tables to new schema
def fetch_and_compute_scanline_ablation(robust_point_count_threshold=64) -> pd.DataFrame:
    query = """
        SELECT e.id AS exp_id,
               e.use_hough_continuity,
               e.use_scanline_conflict_solver,
               e.use_vertical_heuristics,
               e.use_horizontal_heuristics,
               d.name AS dataset,
               dfe.dataset_frame_id NOT IN (
                    SELECT DISTINCT dataset_frame_id
                    FROM dataset_frame_scanline_info_empirical
                    WHERE points_count < ?
               ) AS robust,
               COUNT(CASE WHEN dfe.scanlines_count != ifr.scanlines_count THEN 1 END) AS incorrect_count
        FROM dataset d
             INNER JOIN dataset_frame df ON d.id = df.dataset_id
             INNER JOIN intrinsics_frame_result ifr ON df.id = ifr.dataset_frame_id
             INNER JOIN experiment e ON e.id = ifr.experiment_id
             INNER JOIN dataset_frame_empirical dfe ON df.id = dfe.dataset_frame_id
        GROUP BY exp_id, dataset, robust;
    """

    return pd_read_sqlite_query(Config.DB_PATH, query, params=(robust_point_count_threshold, ))


# TODO complete formatting
def format_to_experiment_configuration(df: pd.DataFrame, robust_only: bool) -> pd.DataFrame:
    configs = experiment_configurations_df().reset_index().rename(columns={"index": "config_order"})

    flags_cols = list(set(configs.columns) - {"exp_name", "config_order"})
    df = df.merge(configs, on=flags_cols)
    df = df.sort_values(by=["dataset", "config_order"], ascending=[False, True]).reset_index()

    incorrect_count_col = "incorrect_count" if not robust_only else "incorrect_count_robust_only"
    df = df.rename(columns={"incorrect_count": incorrect_count_col})

    df = df[["dataset", "exp_name", incorrect_count_col]]
    return df


def experiment_configurations_df() -> pd.DataFrame:
    data = {
        "exp_name": ["E0","E1","E2","E3","E4","E5","E6","E7"],
        "use_hough_continuity": [True, False, True, True, True, True, False, False],
        "use_scanline_conflict_solver": [True, True, False, True, True, True, False, False],
        "use_vertical_heuristics": [True, True, True, False, True, False, True, False],
        "use_horizontal_heuristics": [True, True, True, True, False, False, True, False],
    }

    return pd.DataFrame(data)


if __name__ == "__main__":
    main()