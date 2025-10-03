import os

import pandas as pd

from scripts.common.load_env import load_env
from scripts.local.paper.helper.common import fetch_main_experiment_id, fetch_ri_experiment_id
from scripts.local.paper.helper.metrics import metrics_from_confusion_df
from scripts.local.paper.helper.utils import pd_read_sqlite_query

load_env()

class Config:
    DB_PATH = os.getenv("LOCAL_SQLITE_MASTER_DB")


# TODO CSV files for the sequence plots.
def main():
    print(f"Using database at {Config.DB_PATH}")
    experiment_id = fetch_ri_experiment_id(Config.DB_PATH)
    print(f"Experiment ID: {experiment_id}")

    print("Computing RI metrics from DB...")
    ri_metrics_df = fetch_and_compute_range_image_metrics(experiment_id)
    print(format_final_table(ri_metrics_df))


# TODO update tables to new schema
def fetch_and_compute_range_image_metrics(experiment_id: int) -> pd.DataFrame:
    query = """
        WITH ri_data AS (
            SELECT dataset, method, ri_width, ri_height, chamfer, max_range,
                   10 * log(max_range * max_range / original_to_reconstructed_mse) / log(10) as psnr,
                   sampling_error, experiment_id
            FROM (
                     SELECT experiment_id, d.name AS dataset, rfs.method AS method, ri_width, ri_height, original_to_reconstructed_mse,
                            (original_to_reconstructed_rmse + reconstructed_to_original_rmse) / 2 AS chamfer,
                            (original_points_count - reconstructed_points_count) / original_points_count * 100 as sampling_error,
                            (CASE
                                 WHEN d.name = 'kitti'  THEN 120
                                 WHEN d.name = 'durlar' THEN 200
                                END) AS max_range
                     FROM ri_frame_result AS rfs
                              JOIN dataset_frame df ON rfs.dataset_frame_id = df.id
                              JOIN dataset d ON df.dataset_id = d.id
                 )
        )
        SELECT dataset, method, ri_width, ri_height,
               AVG(chamfer) AS avg_cd, MAX(chamfer) AS max_cd,
               AVG(psnr) AS avg_psnr, MIN(psnr) AS min_psnr,
               AVG(sampling_error) AS avg_se, MAX(sampling_error) AS max_se
        FROM ri_data
        WHERE experiment_id = ?
        GROUP BY dataset, method, ri_width, ri_height
        ORDER BY dataset DESC, method DESC, ri_width, ri_height
    """

    return pd_read_sqlite_query(Config.DB_PATH, query, params=(experiment_id, ))


# TODO complete formatting
def format_final_table(df: pd.DataFrame) -> pd.DataFrame:
    return df


if __name__ == "__main__":
    main()