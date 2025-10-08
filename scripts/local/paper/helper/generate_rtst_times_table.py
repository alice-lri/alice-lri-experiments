import os

import pandas as pd

from scripts.local.runtime import measure_rtst_times
from scripts.local.paper.helper.utils import df_to_latex, write_paper_data


class Config:
    CSV_FILE = os.getenv("RESULT_RTST_TIMES_CSV")
    COLUMNS_RENAME = {
        "naive_encoding_time": ("\\textbf{Encoding Time (ms)}", "Original"),
        "accurate_encoding_time": ("\\textbf{Encoding Time (ms)}", "Modified"),
        "overhead_encoding": ("\\textbf{Encoding Time (ms)}", "Overhead"),
        "naive_decoding_time": ("\\textbf{Decoding Time (ms)}", "Original"),
        "accurate_decoding_time": ("\\textbf{Decoding Time (ms)}", "Modified"),
        "overhead_decoding": ("\\textbf{Decoding Time (ms)}", "Overhead"),
    }
    OUTPUT_FILE = "rtst_times.tex"


def main():
    ensure_csv()
    times_df = pd.read_csv(Config.CSV_FILE)
    times_df = compute_overhead(times_df)
    times_df = group_by_error_threshold(times_df)
    times_df = format_final_table(times_df)

    pd.set_option('display.max_columns', None)
    print(times_df)

    times_latex = df_to_latex(times_df, float_format="%.2f", column_format="r" * (len(times_df.columns) + 1))
    write_paper_data(times_latex, Config.OUTPUT_FILE)


def ensure_csv():
    if os.path.exists(Config.CSV_FILE):
        print(f"File {Config.CSV_FILE} already exists. Will use it.")
        return

    run_answer = input(f"File {Config.CSV_FILE} not found. Run measure_rtst_times.py (y/n)? ")
    if run_answer != "y":
        raise FileNotFoundError(f"File {Config.CSV_FILE} not found")

    measure_rtst_times.main()


def group_by_error_threshold(df):
    metrics = list(Config.COLUMNS_RENAME.keys())
    df_grouped = df[metrics + ["error_threshold"]].groupby("error_threshold")
    df_mean = df_grouped.mean()
    df_std = df_grouped.std()

    df_merged = df_mean.copy()
    df_merged[metrics] = "$" + df_mean[metrics].map(lambda x: f"{x:.2f}") + " \\pm "\
        + df_std[metrics].map(lambda x: f"{x:.2f}") + "$"

    return df_merged


def compute_overhead(df):
    df["overhead_encoding"] = df["accurate_encoding_time"] - df["naive_encoding_time"]
    df["overhead_decoding"] = df["accurate_decoding_time"] - df["naive_decoding_time"]

    return df


def format_final_table(df):
    df = df.rename(columns=Config.COLUMNS_RENAME)
    df.columns = pd.MultiIndex.from_tuples(df.columns)
    df.index.name = "Error Threshold"

    df.index = pd.MultiIndex.from_tuples(
        [(f"{i:.3f}", ) for i in df.index],
        names=df.index.names
    )

    return df


if __name__ == "__main__":
    main()
