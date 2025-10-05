import os
import sqlite3

import pandas as pd

from scripts.common.load_env import load_env
from scripts.local.paper.helper.common import fetch_ri_experiment_id

load_env()

class Config:
    DB_PATH = os.getenv("LOCAL_SQLITE_MASTER_DB")
    KITTI_SEQUENCE = "2011_09_30_drive_0018_sync"
    DURLAR_SEQUENCE = "DurLAR_20211209"
    CD_BY_FRAME_CSVS_FOLDER = os.path.join(os.getenv("PAPER_DATA_DIR"), "cd_by_frame_csvs")


def main():
    print(f"Using database at {Config.DB_PATH}")
    experiment_id = fetch_ri_experiment_id(Config.DB_PATH)
    print(f"Experiment ID: {experiment_id}")

    print("Computing RI metrics from DB...")
    with sqlite3.connect(Config.DB_PATH) as conn:
        create_temp_sql_view(conn)
        ri_metrics_df = fetch_and_compute_range_image_metrics(conn, experiment_id)

        subsets = ri_metrics_df[["dataset", "method", "ri_width", "ri_height"]].drop_duplicates()
        for _, subset in subsets.iterrows():
            output_filename = f"{subset["dataset"]}_{subset["method"]}_{subset["ri_width"]}x{subset["ri_height"]}.csv"
            cd_by_frame_df = fetch_cd_for_frames(conn, experiment_id, subset)

            print(f"Writing {output_filename}...")
            cd_by_frame_df.rename(columns={"chamfer": "CD (m)"})\
                .to_csv(os.path.join(Config.CD_BY_FRAME_CSVS_FOLDER, output_filename), index=False)

    print(format_final_table(ri_metrics_df))


def create_temp_sql_view(conn: sqlite3.Connection):
    query = """
        CREATE TEMP VIEW ri_data AS
        SELECT d.name AS dataset, relative_path, experiment_id, rfs.method AS method, ri_width, ri_height,
            (original_to_reconstructed_rmse + reconstructed_to_original_rmse) / 2 AS chamfer,
            10 * log(max_range * max_range / original_to_reconstructed_mse) / log(10) as psnr,
            (original_points_count - reconstructed_points_count) * 1.0 / original_points_count * 100 as sampling_error,
            d.max_range AS max_range
        FROM ri_frame_result AS rfs
            JOIN dataset_frame df ON rfs.dataset_frame_id = df.id
            JOIN dataset d ON df.dataset_id = d.id
    """

    conn.cursor().execute(query)


# TODO update tables to new schema
def fetch_and_compute_range_image_metrics(conn: sqlite3.Connection, experiment_id: int) -> pd.DataFrame:
    query = """
        SELECT dataset, method, ri_width, ri_height,
               AVG(chamfer) AS avg_cd, MAX(chamfer) AS max_cd,
               AVG(psnr) AS avg_psnr, MIN(psnr) AS min_psnr,
               AVG(sampling_error) AS avg_se, MAX(sampling_error) AS max_se
        FROM ri_data
        WHERE experiment_id = ?
        GROUP BY dataset, method, ri_width, ri_height
        ORDER BY dataset DESC, method DESC, ri_width, ri_height
    """

    return pd.read_sql_query(query, conn, params=(experiment_id, ))


def fetch_cd_for_frames(conn: sqlite3.Connection, experiment_id: int, subset: pd.Series, max_frames:int=1000):
    dataset = subset["dataset"]
    sequence = Config.KITTI_SEQUENCE if dataset == "kitti" else Config.DURLAR_SEQUENCE
    query = """
        SELECT chamfer
        FROM ri_data
        WHERE experiment_id = ? AND dataset = ? AND relative_path LIKE ?
          AND method = ? AND ri_width = ? AND ri_height = ?
        ORDER BY relative_path
        LIMIT ?
    """

    params = (experiment_id, dataset, f'%{sequence}%', subset["method"], subset["ri_width"], subset["ri_height"], max_frames)
    result_df = pd.read_sql_query(query, conn, params=params)
    result_df["frame_index"] = range(len(result_df))

    return result_df[["frame_index", "chamfer"]]


# TODO complete formatting
def format_final_table(df: pd.DataFrame) -> pd.DataFrame:
    return df


if __name__ == "__main__":
    main()