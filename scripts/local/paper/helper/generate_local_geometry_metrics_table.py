import os
import sqlite3
from pathlib import Path

import pandas as pd

from scripts.common.load_env import load_env
from scripts.local.paper.helper.common import fetch_local_geometry_experiment_id
from scripts.local.paper.helper.utils import df_format_dataset_names, df_to_latex, write_paper_data

load_env()


class Config:
    DB_PATH = os.getenv("LOCAL_SQLITE_MASTER_DB")
    OUTPUT_TABLE_TEX = "local_geometry_metrics.tex"

    RENAME_COLUMNS_LEVEL_0 = {
        "point_to_plane": "\\textbf{SP2P (m)}",
    }
    RENAME_COLUMNS_LEVEL_1 = {
        "avg": "AVG",
        "max": "MAX",
    }
    COLUMN_NAMES = {
        "point_to_plane_avg": ("point_to_plane", "avg"),
        "point_to_plane_max": ("point_to_plane", "max"),
    }


def main():
    print(f"Using database at {Config.DB_PATH}")
    experiment_id = fetch_local_geometry_experiment_id(Config.DB_PATH)
    print(f"Experiment ID: {experiment_id}")

    with connect_read_only(Config.DB_PATH) as conn:
        print("Computing local geometry metrics from DB...")
        local_geometry_df = fetch_and_compute_local_geometry_metrics(conn, experiment_id)

    pd.set_option("display.max_columns", None)
    print(local_geometry_df)

    local_geometry_df = format_final_table(local_geometry_df)
    latex = df_to_latex(
        local_geometry_df,
        bold_rows=False,
        multicolumn_format="c",
        column_format="ll" + "r" * len(local_geometry_df.columns),
    )
    write_paper_data(latex, Config.OUTPUT_TABLE_TEX)


def connect_read_only(db_path: str) -> sqlite3.Connection:
    uri = Path(db_path).absolute().as_uri() + "?mode=ro"
    return sqlite3.connect(uri, uri=True)


def fetch_and_compute_local_geometry_metrics(conn: sqlite3.Connection, experiment_id: int) -> pd.DataFrame:
    query = """
        SELECT
            d.name AS dataset,
            lgfr.method,
            lgfr.ri_width,
            lgfr.ri_height,
            COUNT(*) AS frames,
            AVG(lgfr.point_to_plane_mean) AS point_to_plane_avg,
            MAX(lgfr.point_to_plane_mean) AS point_to_plane_max
        FROM local_geometry_frame_result AS lgfr
            JOIN dataset_frame AS df ON lgfr.dataset_frame_id = df.id
            JOIN dataset AS d ON df.dataset_id = d.id
        WHERE lgfr.experiment_id = ?
        GROUP BY d.name, lgfr.method, lgfr.ri_width, lgfr.ri_height
        ORDER BY
            CASE d.name WHEN 'kitti' THEN 0 WHEN 'durlar' THEN 1 ELSE 2 END,
            CASE lgfr.method
                WHEN 'pbea_native' THEN 0
                WHEN 'pbea_x2' THEN 1
                WHEN 'pbea_x4' THEN 2
                WHEN 'pbea_x8' THEN 3
                WHEN 'pbea_x16' THEN 4
                WHEN 'pbea_x32' THEN 5
                WHEN 'alice_lri' THEN 6
                ELSE 7
            END,
            lgfr.ri_width,
            lgfr.ri_height
    """

    return pd.read_sql_query(query, conn, params=(experiment_id,))


def format_final_table(df: pd.DataFrame) -> pd.DataFrame:
    df["Method"] = df.apply(format_method, axis=1)
    df = df.rename(columns={"dataset": "Dataset"})
    df = df.set_index(["Dataset", "Method"])
    df = df.drop(columns=["method", "ri_width", "ri_height", "frames"])

    df.columns = pd.MultiIndex.from_tuples([Config.COLUMN_NAMES[col] for col in df.columns])
    df = df.rename(columns=Config.RENAME_COLUMNS_LEVEL_0, level=0)
    df = df.rename(columns=Config.RENAME_COLUMNS_LEVEL_1, level=1)
    df = df[list(Config.RENAME_COLUMNS_LEVEL_0.values())]
    df = df_format_dataset_names(df)
    df = df.map(lambda x: f"{x:.6f}" if isinstance(x, (float, int)) else str(x))

    ours_mask = df.index.get_level_values("Method").str.contains("ALICE-LRI", regex=False)
    df.loc[ours_mask] = df.loc[ours_mask].map(lambda x: f"$\\mathbf{{{x}}}$")

    return df


def format_method(r: pd.Series) -> str:
    if r["method"] == "alice_lri":
        return f"\\textbf{{ALICE-LRI}} ($\\mathbf{{{r['ri_width']}}} \\times \\mathbf{{{r['ri_height']}}}$)"

    if r["method"] == "pbea_native" or r["method"].startswith("pbea"):
        return f"PBEA ($\\num{{{r['ri_width']}}} \\times \\num{{{r['ri_height']}}}$)"

    return f"{r['method']} ($\\num{{{r['ri_width']}}} \\times \\num{{{r['ri_height']}}}$)"


if __name__ == "__main__":
    main()
