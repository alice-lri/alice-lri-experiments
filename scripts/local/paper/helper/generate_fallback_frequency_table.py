import os
import sqlite3
from pathlib import Path

import pandas as pd

from scripts.common.load_env import load_env
from scripts.local.paper.helper.common import fetch_main_experiment_id
from scripts.local.paper.helper.utils import df_format_dataset_names, df_to_latex, write_paper_data

load_env()


class Config:
    DB_PATH = os.getenv("LOCAL_SQLITE_MASTER_DB")
    ROBUST_POINT_COUNT_THRESHOLD = 64

    OUTPUT_TABLE_FILE = "fallback_frequency.tex"
    OUTPUT_CSV_FILE = "fallback_frequency.csv"

    SUBSET_LABELS = {
        "all": "All",
        "robust_only": f"$n^{{(l)}} \\geq {ROBUST_POINT_COUNT_THRESHOLD}$",
    }
    COLUMNS_RENAME = {
        "dataset": "Dataset",
        "subset": "Subset",
        "total_frames": "\\# Total",
        "any_fallback_frames_merged": "\\# With Fallback",
        "total_scanlines": "\\# Total",
        "any_fallback_scanlines_merged": "\\# With Fallback",
    }


def main():
    print(f"Using database at {Config.DB_PATH}")
    experiment_id = fetch_main_experiment_id(Config.DB_PATH)
    print(f"Experiment ID: {experiment_id}")

    print("Computing fallback frequencies from DB...")
    frame_stats_df = fetch_frame_stats(experiment_id)
    fallback_frequency_df = aggregate_fallback_frequency(frame_stats_df)

    export_csv(fallback_frequency_df)

    table_df = format_final_table(fallback_frequency_df)
    latex = df_to_latex(
        table_df,
        float_format="%.2f",
        column_format="llrrrr",
    )
    write_paper_data(latex, Config.OUTPUT_TABLE_FILE)


def fetch_frame_stats(experiment_id: int) -> pd.DataFrame:
    query = """
        WITH sparse_frames AS (
            SELECT DISTINCT dataset_frame_id
            FROM dataset_frame_scanline_gt
            WHERE points_count < ?
        )
        SELECT d.name AS dataset,
               df.id AS frame_id,
               sf.dataset_frame_id IS NULL AS robust,
               COUNT(scanline.id) AS scanlines,
               SUM(CASE WHEN scanline.vertical_uncertainty > 1e300 THEN 1 ELSE 0 END) AS vertical_fallback_scanlines,
               SUM(CASE WHEN scanline.horizontal_heuristic = 1 THEN 1 ELSE 0 END) AS horizontal_fallback_scanlines,
               SUM(CASE
                   WHEN scanline.vertical_uncertainty > 1e300 OR scanline.horizontal_heuristic = 1
                   THEN 1 ELSE 0
               END) AS any_fallback_scanlines,
               MAX(CASE WHEN scanline.vertical_uncertainty > 1e300 THEN 1 ELSE 0 END) AS vertical_fallback_frame,
               MAX(CASE WHEN scanline.horizontal_heuristic = 1 THEN 1 ELSE 0 END) AS horizontal_fallback_frame,
               MAX(CASE
                   WHEN scanline.vertical_uncertainty > 1e300 OR scanline.horizontal_heuristic = 1
                   THEN 1 ELSE 0
               END) AS any_fallback_frame
        FROM dataset d
                 INNER JOIN dataset_frame df ON df.dataset_id = d.id
                 INNER JOIN intrinsics_frame_result ifr ON ifr.dataset_frame_id = df.id
                 INNER JOIN intrinsics_scanline_result scanline ON scanline.intrinsics_result_id = ifr.id
                 LEFT JOIN sparse_frames sf ON sf.dataset_frame_id = df.id
        WHERE ifr.experiment_id = ?
        GROUP BY d.name, df.id, robust;
    """
    with connect_read_only(Config.DB_PATH) as conn:
        return pd.read_sql_query(
            query,
            conn,
            params=(Config.ROBUST_POINT_COUNT_THRESHOLD, experiment_id),
        )


def connect_read_only(db_path: str) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{Path(db_path).resolve()}?mode=ro", uri=True)


def aggregate_fallback_frequency(frame_stats_df: pd.DataFrame) -> pd.DataFrame:
    all_df = aggregate_subset(frame_stats_df, "all")
    robust_only_df = aggregate_subset(frame_stats_df[frame_stats_df["robust"] == 1], "robust_only")
    df = pd.concat([all_df, robust_only_df], ignore_index=True)

    subset_order = {"all": 0, "robust_only": 1}
    df["subset_order"] = df["subset"].map(subset_order)
    df = df.sort_values(["dataset", "subset_order"], ascending=[False, True]).drop(columns="subset_order")

    percent_cols = [col for col in df.columns if col.endswith("_percent")]
    df[percent_cols] = df[percent_cols].round(6)

    return df


def aggregate_subset(df: pd.DataFrame, subset: str) -> pd.DataFrame:
    grouped = df.groupby("dataset", as_index=False).agg(
        total_frames=("frame_id", "count"),
        total_scanlines=("scanlines", "sum"),
        vertical_fallback_frames=("vertical_fallback_frame", "sum"),
        horizontal_fallback_frames=("horizontal_fallback_frame", "sum"),
        any_fallback_frames=("any_fallback_frame", "sum"),
        vertical_fallback_scanlines=("vertical_fallback_scanlines", "sum"),
        horizontal_fallback_scanlines=("horizontal_fallback_scanlines", "sum"),
        any_fallback_scanlines=("any_fallback_scanlines", "sum"),
    )
    grouped["subset"] = subset

    for fallback_type in ["vertical", "horizontal", "any"]:
        grouped[f"{fallback_type}_fallback_frames_percent"] = (
            grouped[f"{fallback_type}_fallback_frames"] / grouped["total_frames"] * 100
        )
        grouped[f"{fallback_type}_fallback_scanlines_percent"] = (
            grouped[f"{fallback_type}_fallback_scanlines"] / grouped["total_scanlines"] * 100
        )

    return grouped


def export_csv(df: pd.DataFrame):
    target_path = os.path.join(os.getenv("PAPER_DATA_DIR"), Config.OUTPUT_CSV_FILE)
    columns = [
        "dataset",
        "subset",
        "total_frames",
        "vertical_fallback_frames",
        "vertical_fallback_frames_percent",
        "horizontal_fallback_frames",
        "horizontal_fallback_frames_percent",
        "any_fallback_frames",
        "any_fallback_frames_percent",
        "total_scanlines",
        "vertical_fallback_scanlines",
        "vertical_fallback_scanlines_percent",
        "horizontal_fallback_scanlines",
        "horizontal_fallback_scanlines_percent",
        "any_fallback_scanlines",
        "any_fallback_scanlines_percent",
    ]
    df = df[columns]
    df.to_csv(target_path, index=False)
    print(f"CSV data written to {target_path}")


def format_final_table(df: pd.DataFrame) -> pd.DataFrame:
    table_df = df.copy()
    table_df["any_fallback_frames_merged"] = table_df.apply(
        lambda row: format_count_with_percent(row["any_fallback_frames"], row["any_fallback_frames_percent"]),
        axis=1,
    )
    table_df["any_fallback_scanlines_merged"] = table_df.apply(
        lambda row: format_count_with_percent(row["any_fallback_scanlines"], row["any_fallback_scanlines_percent"]),
        axis=1,
    )
    table_df["total_frames"] = table_df["total_frames"].map(format_count)
    table_df["total_scanlines"] = table_df["total_scanlines"].map(format_count)
    table_df["subset"] = table_df["subset"].replace(Config.SUBSET_LABELS)

    table_df = table_df[
        [
            "dataset",
            "subset",
            "total_frames",
            "any_fallback_frames_merged",
            "total_scanlines",
            "any_fallback_scanlines_merged",
        ]
    ]
    table_df = table_df.rename(columns=Config.COLUMNS_RENAME)
    table_df = table_df.set_index(["Dataset", "Subset"])
    table_df.columns = pd.MultiIndex.from_tuples([
        ("\\textbf{Frames}", "\\# Total"),
        ("\\textbf{Frames}", "\\# With Fallback"),
        ("\\textbf{Scanlines}", "\\# Total"),
        ("\\textbf{Scanlines}", "\\# With Fallback"),
    ])
    table_df = df_format_dataset_names(table_df)

    return table_df


def format_count(count: int) -> str:
    return f"\\num{{{int(count)}}}"


def format_count_with_percent(count: int, percent: float) -> str:
    return f"{format_count(count)} ({format_percent(percent)}\\%)"


def format_percent(percent: float) -> str:
    if percent == 0:
        return "0"
    if percent >= 1:
        return f"{percent:.2f}"
    if percent >= 0.1:
        return f"{percent:.3f}"
    return f"{percent:.4f}"


if __name__ == "__main__":
    main()
