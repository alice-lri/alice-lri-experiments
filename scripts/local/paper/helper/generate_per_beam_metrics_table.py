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

    print("Computing MAX and MAE from DB. This may take a while...")
    max_mae_all_df = fetch_and_compute_max_and_mae(experiment_id, robust_only=False).assign(subset="all")
    max_mae_robust_only = fetch_and_compute_max_and_mae(experiment_id, robust_only=True).assign(subset="robust_only")

    pd.set_option('display.max_columns', None)
    max_mae_final_df = pd.concat([max_mae_all_df, max_mae_robust_only])
    print(format_final_table(max_mae_final_df))


# TODO update tables to new schema
def fetch_and_compute_max_and_mae(experiment_id: int, robust_only: bool, robust_point_count_threshold=64) -> pd.DataFrame:
    query = f"""
        WITH scanline_diffs AS (
            SELECT
                d.name AS dataset,
                exp.id AS experiment_id,
                frame.id AS dataset_frame_id,
                scanline_gt.points_count AS points_count,

                scanline.vertical_angle - scanline_gt.vertical_angle AS v_angle_diff,
                scanline.vertical_offset - scanline_gt.vertical_offset AS v_offset_diff,
                scanline.horizontal_offset - scanline_gt.horizontal_offset AS h_offset_diff,
                scanline.horizontal_angle_offset - scanline_gt.horizontal_angle_offset AS h_angle_offset_diff
            FROM dataset d
                     JOIN dataset_frame frame ON d.id = frame.dataset_id
                     JOIN dataset_frame_scanline_info_empirical scanline_gt ON frame.id = scanline_gt.dataset_frame_id
                     JOIN intrinsics_frame_result ifr ON ifr.dataset_frame_id = frame.id
                     JOIN experiment exp ON ifr.experiment_id = exp.id
                     JOIN intrinsics_result_scanline_info scanline ON scanline_gt.scanline_idx = scanline.scanline_idx
                          AND scanline.intrinsics_result_id = ifr.id
        )
        SELECT dataset,
            MAX(ABS(v_angle_diff * 180 / PI())) AS v_angle_max,
            AVG(ABS(v_angle_diff * 180 / PI())) AS v_angle_mae,
            MAX(ABS(v_offset_diff * 1000)) AS v_offset_max,
            AVG(ABS(v_offset_diff * 1000)) AS v_offset_mae,
            MAX(ABS(h_offset_diff * 1000)) AS h_offset_max,
            AVG(ABS(h_offset_diff * 1000)) AS h_offset_mae,
            MAX(ABS(h_angle_offset_diff * 180 / PI())) AS h_angle_offset_max,
            AVG(ABS(h_angle_offset_diff * 180 / PI())) AS h_angle_offset_mae,
            { """ dataset_frame_id NOT IN ( 
                    SELECT dataset_frame_id
                    FROM dataset_frame_scanline_info_empirical 
                    WHERE points_count < ?
                ) as robust_filter""" if robust_only else "1 as robust_filter"
            }
        FROM scanline_diffs
        WHERE experiment_id = ? AND robust_filter
        GROUP BY dataset
    """

    params = (robust_point_count_threshold, experiment_id) if robust_only else (experiment_id,)
    return pd_read_sqlite_query(Config.DB_PATH, query, params=params)


# TODO complete formatting
def format_final_table(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(by=["dataset", "subset"], ascending=[False, True])
    cols = df.columns.tolist()
    cols.insert(cols.index("dataset") + 1, cols.pop(cols.index("subset")))
    df = df[cols]

    return df


if __name__ == "__main__":
    main()
