import os

import pandas as pd
from typing import Callable

from scripts.common.load_env import load_env
from scripts.local.paper.helper.utils import pd_read_sqlite_query, df_to_latex, write_paper_data

load_env()

class Config:
    DB_PATH = os.getenv("LOCAL_SQLITE_MASTER_DB")

    COLS_RENAME_LEVEL_0 = {
        "components": "\\textbf{Algorithm Components}",
        "kitti": "\\textbf{KITTI}",
        "durlar": "\\textbf{DurLAR}"
    }
    COLS_RENAME_LEVEL_1 = {
        "use_hough_continuity": "Hough Continuity",
        "use_scanline_conflict_solver": "Conflict Resolution",
        "use_vertical_heuristics": "Vertical Heuristics",
        "use_horizontal_heuristics": "Horizontal Heuristics",
        "incorrect_scanline": "\\# Incorrect Scanlines Count",
        "incorrect_resolution": "\\# Incorrect Resolutions"
    }
    
    OUTPUT_FILE = "ablation_combined_metrics.tex"


def main():
    print(f"Using database at {Config.DB_PATH}")

    print("Computing scanline ablation results from DB. This may take a while...")
    scanline_ablation_df = generate_ablation_df(fetch_and_compute_scanline_ablation)

    print("Computing resolution ablation results from DB. This will take a long while (go for a coffee)...")
    resolution_ablation_df = generate_ablation_df(fetch_and_compute_resolution_ablation)

    full_ablation_df = generate_full_ablation_df(scanline_ablation_df, resolution_ablation_df)

    pd.set_option('display.max_columns', None)
    print(full_ablation_df)

    full_ablation_df = format_final_table(full_ablation_df)
    latex = df_to_latex(full_ablation_df, column_format="lccccrrrr")
    write_paper_data(latex, Config.OUTPUT_FILE)


def generate_ablation_df(fetch_func: Callable[[], pd.DataFrame]) -> pd.DataFrame:
    scanline_ablation_all_df = fetch_func()
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


def fetch_and_compute_scanline_ablation(robust_point_count_threshold=64) -> pd.DataFrame:
    query = """
        SELECT e.id AS exp_id,
               e.use_hough_continuity,
               e.use_scanline_conflict_solver,
               e.use_vertical_heuristics,
               e.use_horizontal_heuristics,
               d.name AS dataset,
               dfgt.dataset_frame_id NOT IN (
                    SELECT DISTINCT dataset_frame_id
                    FROM dataset_frame_scanline_gt
                    WHERE points_count < ?
               ) AS robust,
               COUNT(CASE WHEN dfgt.scanlines_count != ifr.scanlines_count THEN 1 END) AS incorrect_count
        FROM dataset d
             INNER JOIN dataset_frame df ON d.id = df.dataset_id
             INNER JOIN intrinsics_frame_result ifr ON df.id = ifr.dataset_frame_id
             INNER JOIN intrinsics_experiment e ON e.id = ifr.experiment_id
             INNER JOIN dataset_frame_gt dfgt ON df.id = dfgt.dataset_frame_id
        GROUP BY exp_id, dataset, robust;
    """

    return pd_read_sqlite_query(Config.DB_PATH, query, params=(robust_point_count_threshold, ))


def fetch_and_compute_resolution_ablation(robust_point_count_threshold=64) -> pd.DataFrame:
    query = """
        SELECT e.id AS exp_id,
            e.use_hough_continuity,
            e.use_scanline_conflict_solver,
            e.use_vertical_heuristics,
            e.use_horizontal_heuristics,
            d.name AS dataset,
            scanline_gt.dataset_frame_id NOT IN (
                SELECT DISTINCT dataset_frame_id
                FROM dataset_frame_scanline_gt
                WHERE points_count < ?
            ) AS robust,
            COUNT(CASE WHEN 
                laser_gt.horizontal_resolution != COALESCE(scanline.horizontal_resolution, -1)
            THEN 1 END) AS incorrect_count
        FROM dataset d
                 INNER JOIN dataset_frame df ON df.dataset_id = d.id
                 INNER JOIN intrinsics_frame_result ifr ON ifr.dataset_frame_id = df.id
                 INNER JOIN intrinsics_experiment e ON e.id = ifr.experiment_id
                 INNER JOIN dataset_frame_scanline_gt scanline_gt ON scanline_gt.dataset_frame_id = df.id
                 INNER JOIN dataset_laser_gt laser_gt ON laser_gt.id = scanline_gt.laser_id
                 LEFT JOIN intrinsics_scanline_result scanline ON scanline.intrinsics_result_id = ifr.id
                    AND scanline.scanline_idx = scanline_gt.scanline_idx
        GROUP BY exp_id, dataset, robust
    """

    return pd_read_sqlite_query(Config.DB_PATH, query, params=(robust_point_count_threshold, ))


def format_to_experiment_configuration(df: pd.DataFrame, robust_only: bool) -> pd.DataFrame:
    configs = experiment_configurations_df().reset_index().rename(columns={"index": "config_order"})

    flags_cols = [col for col in configs.columns if col not in ["exp_name", "config_order"]]
    df = df.merge(configs, on=flags_cols)
    df = df.sort_values(by=["dataset", "config_order"], ascending=[False, True]).reset_index()

    incorrect_count_col = "incorrect_count" if not robust_only else "incorrect_count_robust_only"
    df = df.rename(columns={"incorrect_count": incorrect_count_col})

    df = df[["dataset", "exp_name"] + flags_cols + [incorrect_count_col]]
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


def generate_full_ablation_df(scanline_df: pd.DataFrame, resolution_df: pd.DataFrame) -> pd.DataFrame:
    df = merge_ablation_parts(scanline_df, resolution_df)
    df = pivot_full_df(df)

    return df


def merge_ablation_parts(scanline_df: pd.DataFrame, resolution_df: pd.DataFrame) -> pd.DataFrame:
    original_measure_columns = ["incorrect_count", "incorrect_count_robust_only"]
    merge_cols = [col for col in scanline_df.columns if col not in original_measure_columns]
    merge_cols_func = lambda row: f"{row['incorrect_count']} ({row['incorrect_count_robust_only']})"

    scanline_df["incorrect"] = scanline_df.apply(merge_cols_func, axis=1)
    resolution_df["incorrect"] = resolution_df.apply(merge_cols_func, axis=1)
    scanline_df = scanline_df.drop(columns=original_measure_columns)
    resolution_df = resolution_df.drop(columns=original_measure_columns)

    return pd.merge(scanline_df, resolution_df, on=merge_cols, suffixes=("_scanline", "_resolution"))


def pivot_full_df(df: pd.DataFrame) -> pd.DataFrame:
    pivoted_df = df.pivot(index="exp_name", columns="dataset", values=["incorrect_scanline", "incorrect_resolution"])
    pivoted_df.columns = pivoted_df.columns.swaplevel()
    pivoted_df = pivoted_df.sort_index(axis=1, level=0, ascending=False)

    flags_cols = [c for c in df.columns if c.startswith("use_")]
    flags_df = df[["exp_name"] + flags_cols].drop_duplicates("exp_name").set_index("exp_name")
    flags_df.columns = pd.MultiIndex.from_product([["components"], flags_df.columns])

    return pd.merge(flags_df, pivoted_df, left_index=True, right_index=True)


def format_final_table(df: pd.DataFrame) -> pd.DataFrame:
    flags_cols = [c for c in df.columns if c[1].startswith("use_")]
    df[flags_cols] = df[flags_cols].map(lambda x: "\\checkmark" if x == 1 else "")

    df = df.rename(columns=Config.COLS_RENAME_LEVEL_0, level=0)
    df = df.rename(columns=Config.COLS_RENAME_LEVEL_1, level=1)
    df.index.name = " "

    return df


if __name__ == "__main__":
    main()
