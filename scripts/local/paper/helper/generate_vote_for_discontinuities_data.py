import os

import alice_lri
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from scripts.common.helper.point_cloud import load_binary
from scripts.common.helper.ri.ri_default_mapper import RangeImageDefaultMapper
from scripts.common.helper.ri.ri_utils import point_cloud_to_range_image, range_image_to_point_cloud
from scripts.common.load_env import load_env
from scripts.local.paper.helper.utils import save_point_cloud_visualization, save_range_image

load_env()


class Config:
    REGULAR_CSV = os.path.join(os.getenv("PAPER_DATA_DIR"), "hough_continuity_regular.csv")
    CONTINUOUS_CSV = os.path.join(os.getenv("PAPER_DATA_DIR"), "hough_continuity_continuous.csv")


def main():
    dims = (16, 8)
    accumulator_regular = np.zeros(dims)
    accumulator_continuous = np.zeros(dims)

    fill_accumulator(accumulator_regular, False)
    fill_accumulator(accumulator_continuous, True)

    # Save as long-form (x,y,z) CSVs (easy to inspect and plot in PGFPlots)
    to_long_csv(accumulator_regular, Config.REGULAR_CSV)
    to_long_csv(accumulator_continuous, Config.CONTINUOUS_CSV)


def fill_accumulator(accumulator: np.ndarray, use_continuity: bool):
    dims = accumulator.shape
    line1 = lambda x: -2 * x + dims[0] - 1
    line2 = lambda x: 2 * x
    lines = [line1, line2]

    for line, vote in zip(lines, [1, 2]):
        previous_y = -1

        for x in range(dims[1]):
            y = line(x)

            if y < 0 or y >= dims[0]:
                continue

            accumulator[np.round(y).astype(int), x] += vote

            if use_continuity and previous_y != -1:
                y_min = min(previous_y, y)
                y_max = max(previous_y, y)

                for yy in range(y_min + 1, y_max):
                    accumulator[yy, x - 1] += vote
                    accumulator[yy, x] += vote

            previous_y = y


def to_long_csv(accumulator, path):
    h, w = accumulator.shape
    xs, ys = np.meshgrid(np.arange(w), np.arange(h))
    pd.DataFrame({"x": xs.ravel(), "y": ys.ravel(), "z": accumulator.ravel()}).to_csv(path, index=False)


if __name__ == "__main__":
    main()