import os

import pandas as pd

from scripts.local.runtime import measure_rtst_times
from scripts.local.paper.helper.utils import df_to_latex, write_paper_data


class Config:
    CSV_FILE = os.getenv("RESULT_RTST_TIMES_CSV")
    CSV_COLUMNS = {
        "naive_encoding_time": ("\\textbf{Encoding time (ms)}", "Original"),
        "accurate_encoding_time": ("\\textbf{Encoding time (ms)}", "Ours"),
        "overhead_encoding": ("\\textbf{Encoding time (ms)}", "Overhead"),
        "naive_decoding_time": ("\\textbf{Decoding time (ms)}", "Original"),
        "accurate_decoding_time": ("\\textbf{Decoding time (ms)}", "Ours"),
        "overhead_decoding": ("\\textbf{Decoding time (ms)}", "Overhead"),
    }


def ensure_csv():
    if os.path.exists(Config.CSV_FILE):
        print(f"File {Config.CSV_FILE} already exists. Will use it.")
        return

    run_answer = input(f"File {Config.CSV_FILE} not found. Run measure_rtst_times.py (y/n)? ")
    if run_answer != "y":
        raise FileNotFoundError(f"File {Config.CSV_FILE} not found")

    measure_rtst_times.main()


def group_by_error_threshold(df):
    return df[list(Config.CSV_COLUMNS.keys()) + ["error_threshold"]].groupby("error_threshold").mean()


def compute_overhead(df):
    df["overhead_encoding"] = df["accurate_encoding_time"] - df["naive_encoding_time"]
    df["overhead_decoding"] = df["accurate_decoding_time"] - df["naive_decoding_time"]

    return df


def add_human_readable_columns(df, drop_original=False):
    for col, human_col in Config.CSV_COLUMNS.items():
        df[human_col] = df[col]
        if drop_original:
            df = df.drop(columns=col)

    df.columns = pd.MultiIndex.from_tuples(df.columns)
    df.index.name = "Error threshold"

    df.index = pd.MultiIndex.from_tuples(
        [(f"{i:.3f}", ) for i in df.index],
        names=df.index.names
    )

    return df


def main():
    ensure_csv()
    times_df = pd.read_csv(Config.CSV_FILE)
    times_df = compute_overhead(times_df)
    times_df = group_by_error_threshold(times_df)
    times_df = add_human_readable_columns(times_df, drop_original=True)
    times_latex = df_to_latex(times_df, bold_rows=True, escape=False, multicolumn_format="c", multirow=True, float_format="%.2f")

    write_paper_data(times_latex, "rtst_times.tex")


if __name__ == "__main__":
    main()
