import os

import pandas as pd

from scripts.common.load_env import load_env
from scripts.local.paper.helper.common import fetch_compression_experiment_id
from scripts.local.paper.helper.utils import pd_read_sqlite_query

load_env()

class Config:
    DB_PATH = os.getenv("LOCAL_SQLITE_MASTER_DB")
    CD_BY_FRAME_CSVS_FOLDER = os.path.join(os.getenv("PAPER_DATA_DIR"), "cd_by_frame_csvs")


def main():
    print(f"Using database at {Config.DB_PATH}")
    experiment_id = fetch_compression_experiment_id(Config.DB_PATH)
    print(f"Experiment ID: {experiment_id}")

    print("Computing RTST metrics from DB...")
    rtst_metrics = fetch_and_compute_range_image_metrics(experiment_id)

    print(format_final_table(rtst_metrics))


# TODO update tables to new schema
def fetch_and_compute_range_image_metrics(experiment_id: int) -> pd.DataFrame:
    query = """
        SELECT error_threshold,
               AVG(original_size_bytes * 1.0 / naive_size_bytes) AS cr_base,
               AVG(original_size_bytes * 1.0 / accurate_size_bytes) AS cr_alice,
               AVG((original_to_naive_rmse + naive_to_original_rmse) / 2) AS chamfer_base,
               AVG((original_to_accurate_rmse + accurate_to_original_rmse) / 2) AS chamfer_alice,
               AVG(10 * LOG(max_range * max_range / original_to_naive_mse) / LOG(10)) AS psnr_base,
               AVG(10 * LOG(max_range * max_range / original_to_accurate_mse) / LOG(10)) AS psnr_alice,
               AVG((original_points_count - naive_points_count) * 1.0 / original_points_count * 100) AS sampling_error_base,
               AVG((original_points_count - accurate_points_count) * 1.0 / original_points_count * 100) AS sampling_error_alice
        FROM compression_frame_result AS cfs
                 JOIN dataset_frame df ON cfs.dataset_frame_id = df.id
                 JOIN dataset d ON df.dataset_id = d.id
        WHERE experiment_id = ?
        GROUP BY error_threshold
        ORDER BY error_threshold
    """

    return pd_read_sqlite_query(Config.DB_PATH, query, params=(experiment_id, ))


# TODO complete formatting
def format_final_table(df: pd.DataFrame) -> pd.DataFrame:
    return df


if __name__ == "__main__":
    main()