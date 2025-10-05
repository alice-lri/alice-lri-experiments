import os
import subprocess

import pandas as pd

from scripts.local.runtime import measure_rtst_times
from scripts.local.paper.helper.utils import df_to_latex, write_paper_data


class Config:
    CSV_FILE = os.getenv("RESULT_ALICE_TIMES_CSV")
    MEASURE_TIMES_EXECUTABLE = os.getenv("ALICE_MEASURE_TIMES_EXECUTABLE_PATH")


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

    print(times_df)


def ensure_csv():
    if os.path.exists(Config.CSV_FILE):
        print(f"File {Config.CSV_FILE} already exists. Will use it.")
        return

    run_answer = input(f"File {Config.CSV_FILE} not found. Run measure_times.cpp (y/n)? ")
    if run_answer != "y":
        raise FileNotFoundError(f"File {Config.CSV_FILE} not found")

    subprocess.run(Config.MEASURE_TIMES_EXECUTABLE, check=True, text=True)


if __name__ == "__main__":
    main()
