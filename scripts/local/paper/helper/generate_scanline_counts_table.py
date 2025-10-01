import os
import sqlite3

import pandas as pd
from alice_lri import Intrinsics

from scripts.common.helper.entities import IntrinsicsFrameResult
from scripts.local.runtime import measure_rtst_times
from scripts.local.paper.helper.utils import df_to_latex, write_paper_data, df_from_sql_table


class Config:
    DB_PATH = os.getenv("LOCAL_SQLITE_MASTER_DB")


def main():
    conn = sqlite3.connect(Config.DB_PATH)
    frame_results_df = df_from_sql_table(IntrinsicsFrameResult.__table__, conn)
    frame_gt_df = df_from_sql_table()

    print(df)


if __name__ == "__main__":
    main()
