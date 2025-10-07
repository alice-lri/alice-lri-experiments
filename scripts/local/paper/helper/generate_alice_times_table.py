import os
import subprocess

import pandas as pd

from scripts.local.runtime import measure_rtst_times
from scripts.local.paper.helper.utils import df_to_latex, write_paper_data, df_format_dataset_names


class Config:
    CSV_FILE = os.getenv("RESULT_ALICE_TIMES_CSV")
    MEASURE_TIMES_EXECUTABLE = os.getenv("ALICE_MEASURE_TIMES_EXECUTABLE_PATH")

    COLUMNS_RENAME = {
        'dataset': '\\textbf{Dataset}',
        'train_time_merged': '\\textbf{Estimation (s)}',
        'project_time_merged': '\\textbf{Proj. (ms)}',
        'unproject_time_merged': '\\textbf{Unproj. (ms)}',
    }
    VALUES_REPLACE = {
        "kitti": "\\textbf{KITTI}",
        "durlar": "\\textbf{DurLAR}"
    }
    OUTPUT_FILE = "runtime_performance.tex"


def main():
    ensure_csv()
    times_df = pd.read_csv(Config.CSV_FILE)
    times_df['train_time_s'] = times_df['train_time_s']
    times_df['project_time_ms'] = times_df['project_time_s'] * 1000
    times_df['unproject_time_ms'] = times_df['unproject_time_s'] * 1000
    times_df = times_df.groupby('dataset').agg({
        'train_time_s': ['mean', 'std'],
        'project_time_ms': ['mean', 'std'],
        'unproject_time_ms': ['mean', 'std']
    }).round(1)

    pd.set_option('display.max_columns', None)
    print(times_df)

    times_df = format_final_table(times_df)
    latex = df_to_latex(times_df, index=False, multirow=False, multicolumn=False, column_format='l' + 'r' * (len(times_df.columns) - 1))
    write_paper_data(latex, Config.OUTPUT_FILE)


def ensure_csv():
    if os.path.exists(Config.CSV_FILE):
        print(f"File {Config.CSV_FILE} already exists. Will use it.")
        return

    run_answer = input(f"File {Config.CSV_FILE} not found. Run measure_times.cpp (y/n)? ")
    if run_answer != "y":
        raise FileNotFoundError(f"File {Config.CSV_FILE} not found")

    subprocess.run(Config.MEASURE_TIMES_EXECUTABLE, check=True, text=True)


def format_final_table(df: pd.DataFrame) -> pd.DataFrame:
    df['train_time_merged'] = "$" + df[('train_time_s', 'mean')].astype(str) + ' \\pm ' + df[('train_time_s', 'std')].astype(str) + "$"
    df['project_time_merged'] = "$" + df[('project_time_ms', 'mean')].astype(str) + ' \\pm ' + df[('project_time_ms', 'std')].astype(str) + "$"
    df['unproject_time_merged'] = "$" + df[('unproject_time_ms', 'mean')].astype(str) + ' \\pm ' + df[('unproject_time_ms', 'std')].astype(str) + "$"
    df = df.sort_values(by="dataset", ascending=False)
    df = df.reset_index()

    df = df.rename(columns=Config.COLUMNS_RENAME)
    df = df[list(Config.COLUMNS_RENAME.values())]
    df.columns = df.columns.droplevel(1)
    df = df_format_dataset_names(df, bold=True)

    return df[list(Config.COLUMNS_RENAME.values())]


if __name__ == "__main__":
    main()
