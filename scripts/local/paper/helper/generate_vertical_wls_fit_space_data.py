import argparse
import os
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from scripts.common.helper.ground_truth import compute_ground_truth
from scripts.common.helper.point_cloud import calculate_phi, calculate_range, calculate_range_xy, load_binary
from scripts.common.load_env import load_env

load_env()


@dataclass(frozen=True)
class FrameCase:
    dataset: str
    frame_id: int
    relative_path: str
    true_scanlines: int
    predicted_scanlines: int
    min_points: int
    sparse_scanlines: int


class Config:
    DB_PATH = os.getenv("LOCAL_SQLITE_MASTER_DB")
    DURLAR_PATH = os.getenv("LOCAL_DURLAR_PATH")
    PAPER_DATA_DIR = os.getenv("PAPER_MANUSCRIPT_DATA_DIR") or os.getenv("PAPER_DATA_DIR")
    DEFAULT_FRAME_ID = 150476
    ROBUST_POINT_COUNT_THRESHOLD = 64
    BAD_WLS_OFFSET_THRESHOLD_M = 0.05
    MAIN_XLIM = (0.0, 0.34)
    ZOOM_YLIM = (18.55, 21.7)
    ZOOM_X_PADDING = 0.0018
    MAX_MAIN_POINTS_PER_SCANLINE = 35
    OUTPUT_PREFIX = "vertical_wls_fit_space"


def main():
    parser = argparse.ArgumentParser(
        description="Export data for the DurLAR vertical WLS fitting-space PGFPlots figure."
    )
    parser.add_argument("--frame-id", type=int, default=Config.DEFAULT_FRAME_ID)
    parser.add_argument("--output-dir", default=Config.PAPER_DATA_DIR)
    parser.add_argument(
        "--bad-offset-threshold-mm",
        type=float,
        default=Config.BAD_WLS_OFFSET_THRESHOLD_M * 1000.0,
        help="Threshold used to mark non-heuristic vertical-offset errors.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    frame = fetch_frame_case(args.frame_id)
    data = build_frame_data(frame)
    status = fetch_vertical_status(frame, args.bad_offset_threshold_mm / 1000.0)
    export_pgfplots_data(frame, data, status, output_dir)

    print(f"Exported vertical WLS figure data to {output_dir}")
    print(f"Frame: {frame.frame_id} ({frame.relative_path})")
    print(f"Highlighted scanlines: {sorted(status['highlighted'])}")


def connect_read_only() -> sqlite3.Connection:
    return sqlite3.connect(f"file:{Path(Config.DB_PATH).resolve()}?mode=ro", uri=True)


def fetch_frame_case(frame_id: int) -> FrameCase:
    with connect_read_only() as conn:
        df = pd.read_sql_query(
            """
            WITH gt_stats AS (
                SELECT d.name AS dataset,
                       df.id AS frame_id,
                       df.relative_path,
                       dfgt.scanlines_count AS true_scanlines,
                       MIN(scanline_gt.points_count) AS min_points,
                       SUM(CASE WHEN scanline_gt.points_count < ? THEN 1 ELSE 0 END) AS sparse_scanlines
                FROM dataset d
                         JOIN dataset_frame df ON df.dataset_id = d.id
                         JOIN dataset_frame_gt dfgt ON dfgt.dataset_frame_id = df.id
                         JOIN dataset_frame_scanline_gt scanline_gt ON scanline_gt.dataset_frame_id = df.id
                WHERE df.id = ?
                GROUP BY df.id
            ),
            result_stats AS (
                SELECT dataset_frame_id AS frame_id,
                       scanlines_count AS predicted_scanlines
                FROM intrinsics_frame_result
                WHERE experiment_id = 1
                  AND dataset_frame_id = ?
            )
            SELECT gt_stats.*,
                   result_stats.predicted_scanlines
            FROM gt_stats
                     JOIN result_stats ON result_stats.frame_id = gt_stats.frame_id;
            """,
            conn,
            params=(Config.ROBUST_POINT_COUNT_THRESHOLD, frame_id, frame_id),
        )

    if df.empty:
        raise ValueError(f"Frame {frame_id} not found in the main intrinsics experiment.")

    row = df.iloc[0]
    return FrameCase(
        dataset=row["dataset"],
        frame_id=int(row["frame_id"]),
        relative_path=row["relative_path"],
        true_scanlines=int(row["true_scanlines"]),
        predicted_scanlines=int(row["predicted_scanlines"]),
        min_points=int(row["min_points"]),
        sparse_scanlines=int(row["sparse_scanlines"]),
    )


def build_frame_data(frame: FrameCase) -> dict[str, np.ndarray]:
    points, _ = load_binary(resolve_frame_path(frame))
    gt = fetch_dataset_gt(frame.dataset)
    scanline_ids, _ = compute_ground_truth(
        points,
        gt["vertical_angles"],
        gt["vertical_offsets"],
        gt["horizontal_offsets"],
        gt["horizontal_resolutions"],
    )

    ranges = calculate_range(points)
    phis = calculate_phi(points)
    bounds = compute_vertical_bounds(points, gt["vertical_offsets"][scanline_ids])

    return {
        "inv_range": 1.0 / ranges,
        "phi_deg": np.rad2deg(phis),
        "scanline_ids": scanline_ids,
        "bounds": bounds,
        "gt_vertical_angles": gt["vertical_angles"],
        "gt_vertical_offsets": gt["vertical_offsets"],
    }


def resolve_frame_path(frame: FrameCase) -> str:
    if frame.dataset != "durlar":
        raise ValueError(f"Only DurLAR frames are supported by this figure, got {frame.dataset}.")
    return os.path.join(Config.DURLAR_PATH, frame.relative_path)


def fetch_dataset_gt(dataset_name: str) -> dict[str, np.ndarray]:
    with connect_read_only() as conn:
        df = pd.read_sql_query(
            """
            SELECT laser.vertical_angle,
                   laser.vertical_offset,
                   laser.horizontal_offset,
                   laser.horizontal_resolution
            FROM dataset_laser_gt laser
                     JOIN dataset d ON d.id = laser.dataset_id
            WHERE d.name = ?
            ORDER BY laser.vertical_angle ASC;
            """,
            conn,
            params=(dataset_name,),
        )

    return {
        "vertical_angles": df["vertical_angle"].to_numpy(),
        "vertical_offsets": df["vertical_offset"].to_numpy(),
        "horizontal_offsets": df["horizontal_offset"].to_numpy(),
        "horizontal_resolutions": df["horizontal_resolution"].to_numpy(),
    }


def fetch_vertical_status(frame: FrameCase, bad_offset_threshold_m: float) -> dict:
    with connect_read_only() as conn:
        gt = pd.read_sql_query(
            """
            SELECT laser.laser_idx,
                   laser.vertical_angle,
                   laser.vertical_offset
            FROM dataset_frame_scanline_gt scanline_gt
                     JOIN dataset_laser_gt laser ON laser.id = scanline_gt.laser_id
            WHERE scanline_gt.dataset_frame_id = ?
            ORDER BY laser.vertical_angle ASC;
            """,
            conn,
            params=(frame.frame_id,),
        )
        estimated = pd.read_sql_query(
            """
            SELECT scanline.scanline_idx,
                   scanline.vertical_angle,
                   scanline.vertical_offset,
                   scanline.vertical_uncertainty
            FROM intrinsics_frame_result ifr
                     JOIN intrinsics_scanline_result scanline ON scanline.intrinsics_result_id = ifr.id
            WHERE ifr.dataset_frame_id = ?
              AND ifr.experiment_id = 1
            ORDER BY scanline.vertical_angle ASC;
            """,
            conn,
            params=(frame.frame_id,),
        )

    gt_angles = gt["vertical_angle"].to_numpy()
    gt_offsets = gt["vertical_offset"].to_numpy()
    gt_ids = gt["laser_idx"].astype(int).to_numpy()

    used_gt_ids: set[int] = set()
    fallback_ids: set[int] = set()
    bad_wls_ids: set[int] = set()
    estimated_lines: dict[int, dict[str, float]] = {}

    for _, row in estimated.iterrows():
        diffs = np.abs(gt_angles - row["vertical_angle"])
        for gt_order_idx in np.argsort(diffs):
            gt_id = int(gt_ids[gt_order_idx])
            if gt_id in used_gt_ids:
                continue

            used_gt_ids.add(gt_id)
            estimated_lines[gt_id] = {
                "vertical_angle": float(row["vertical_angle"]),
                "vertical_offset": float(row["vertical_offset"]),
                "vertical_uncertainty": float(row["vertical_uncertainty"]),
            }

            if row["vertical_uncertainty"] > 1e300:
                fallback_ids.add(gt_id)
            elif abs(row["vertical_offset"] - gt_offsets[gt_order_idx]) > bad_offset_threshold_m:
                bad_wls_ids.add(gt_id)
            break

    missing_ids = set(int(gt_id) for gt_id in gt_ids if int(gt_id) not in used_gt_ids)
    return {
        "highlighted": fallback_ids | bad_wls_ids | missing_ids,
        "fallback": fallback_ids,
        "bad_wls": bad_wls_ids,
        "missing": missing_ids,
        "estimated_lines": estimated_lines,
    }


def export_pgfplots_data(frame: FrameCase, data: dict[str, np.ndarray], status: dict, output_dir: Path):
    prefix = Config.OUTPUT_PREFIX
    zoom_xlim = compute_zoom_xlim(data, status)
    zoom_ylim = Config.ZOOM_YLIM

    points_df = pd.DataFrame(
        {
            "x": data["inv_range"],
            "y": data["phi_deg"],
            "scanline": data["scanline_ids"],
            "scanline_norm": data["scanline_ids"] / data["scanline_ids"].max(),
        }
    )
    points_df["scanline_color"] = points_df["scanline"] % 10
    main_points_df = sample_main_points(points_df, status)
    zoom_points_df = points_df[
        (points_df["x"] >= zoom_xlim[0])
        & (points_df["x"] <= zoom_xlim[1])
        & (points_df["y"] >= zoom_ylim[0])
        & (points_df["y"] <= zoom_ylim[1])
    ]
    main_points_df.to_csv(output_dir / f"{prefix}_main_points.csv", index=False, float_format="%.9g")
    zoom_points_df.to_csv(output_dir / f"{prefix}_zoom_points.csv", index=False, float_format="%.9g")

    line_tables = build_line_tables(data, status, Config.MAIN_XLIM)
    for name, rows in line_tables.items():
        write_line_table(output_dir / f"{prefix}_{name}_lines.csv", rows)

    write_metadata(output_dir / f"{prefix}_metadata.tex", frame, status, zoom_xlim, zoom_ylim)


def sample_main_points(points_df: pd.DataFrame, status: dict) -> pd.DataFrame:
    sampled_groups = []
    highlighted = set(status["highlighted"])

    for scanline, group in points_df.groupby("scanline", sort=True):
        if int(scanline) in highlighted:
            sampled_groups.append(group)
            continue

        if len(group) <= Config.MAX_MAIN_POINTS_PER_SCANLINE:
            sampled_groups.append(group)
            continue

        sample_idx = np.linspace(0, len(group) - 1, Config.MAX_MAIN_POINTS_PER_SCANLINE, dtype=int)
        sampled_groups.append(group.iloc[sample_idx])

    return pd.concat(sampled_groups, ignore_index=True)


def compute_zoom_xlim(data: dict[str, np.ndarray], status: dict) -> tuple[float, float]:
    scanline_ids = data["scanline_ids"]
    highlighted = sorted(status["highlighted"])
    if not highlighted:
        highlighted = sorted(np.unique(scanline_ids))[-8:]

    lower = max(min(highlighted) - 3, int(scanline_ids.min()))
    upper = min(max(highlighted) + 1, int(scanline_ids.max()))
    mask = (scanline_ids >= lower) & (scanline_ids <= upper)
    x = data["inv_range"][mask]
    xlim = padded_limits(float(x.min()), float(x.max()), min_width=0.018)
    return xlim[0] - Config.ZOOM_X_PADDING, xlim[1] + Config.ZOOM_X_PADDING


def padded_limits(lower: float, upper: float, min_width: float) -> tuple[float, float]:
    center = 0.5 * (lower + upper)
    width = max(upper - lower, min_width)
    padding = 0.12 * width
    return center - 0.5 * width - padding, center + 0.5 * width + padding


def build_line_tables(data: dict[str, np.ndarray], status: dict, line_x_range: tuple[float, float]) -> dict:
    scanline_ids = data["scanline_ids"]
    unique_scanlines = np.unique(scanline_ids)
    counts = np.bincount(scanline_ids, minlength=int(unique_scanlines.max()) + 1)
    tables = {
        "estimated": [],
        "fallback": [],
        "bad_wls": [],
        "gt_reference": [],
    }

    for scanline_idx in unique_scanlines:
        scanline_idx = int(scanline_idx)
        xx = np.array(line_x_range)
        gt_yy = np.rad2deg(
            data["gt_vertical_offsets"][scanline_idx] * xx + data["gt_vertical_angles"][scanline_idx]
        )
        tables["gt_reference"].append(segment_rows(xx, gt_yy))

        mask = scanline_ids == scanline_idx
        if scanline_idx in status["missing"]:
            continue
        if scanline_idx in status["estimated_lines"]:
            line = status["estimated_lines"][scanline_idx]
            slope = line["vertical_offset"]
            intercept = line["vertical_angle"]
        elif mask.sum() >= 2:
            slope, intercept = weighted_linear_fit(data["inv_range"][mask], np.deg2rad(data["phi_deg"][mask]), data["bounds"][mask])
        else:
            continue

        yy = np.rad2deg(slope * xx + intercept)
        rows = segment_rows(xx, yy)
        if scanline_idx in status["fallback"]:
            tables["fallback"].append(rows)
        elif scanline_idx in status["bad_wls"]:
            tables["bad_wls"].append(rows)
        elif counts[scanline_idx] >= Config.ROBUST_POINT_COUNT_THRESHOLD or mask.sum() >= 2:
            tables["estimated"].append(rows)

    return tables


def segment_rows(x: np.ndarray, y: np.ndarray) -> list[tuple[float, float]]:
    return [(float(x[0]), float(y[0])), (float(x[1]), float(y[1])), (np.nan, np.nan)]


def write_line_table(path: Path, segments: list[list[tuple[float, float]]]):
    with path.open("w", encoding="utf-8") as f:
        f.write("x,y\n")
        for segment in segments:
            for x, y in segment:
                if np.isnan(x) or np.isnan(y):
                    f.write("nan,nan\n")
                else:
                    f.write(f"{x:.9g},{y:.9g}\n")


def write_metadata(
    path: Path,
    frame: FrameCase,
    status: dict,
    zoom_xlim: tuple[float, float],
    zoom_ylim: tuple[float, float],
):
    highlighted = ",".join(str(scanline) for scanline in sorted(status["highlighted"]))
    fallback = ",".join(str(scanline) for scanline in sorted(status["fallback"]))
    bad_wls = ",".join(str(scanline) for scanline in sorted(status["bad_wls"]))
    missing = ",".join(str(scanline) for scanline in sorted(status["missing"]))

    path.write_text(
        "\n".join(
            [
                f"\\newcommand{{\\VerticalWLSFrameId}}{{{frame.frame_id}}}",
                f"\\newcommand{{\\VerticalWLSFramePath}}{{{frame.relative_path}}}",
                f"\\newcommand{{\\VerticalWLSTrueScanlines}}{{{frame.true_scanlines}}}",
                f"\\newcommand{{\\VerticalWLSPredictedScanlines}}{{{frame.predicted_scanlines}}}",
                f"\\newcommand{{\\VerticalWLSSparseScanlines}}{{{frame.sparse_scanlines}}}",
                f"\\newcommand{{\\VerticalWLSMinPoints}}{{{frame.min_points}}}",
                f"\\newcommand{{\\VerticalWLSHighlightedScanlines}}{{{highlighted}}}",
                f"\\newcommand{{\\VerticalWLSFallbackScanlines}}{{{fallback}}}",
                f"\\newcommand{{\\VerticalWLSBadWLSScanlines}}{{{bad_wls}}}",
                f"\\newcommand{{\\VerticalWLSMissingScanlines}}{{{missing}}}",
                f"\\newcommand{{\\VerticalWLSMainXMin}}{{{Config.MAIN_XLIM[0]:.9g}}}",
                f"\\newcommand{{\\VerticalWLSMainXMax}}{{{Config.MAIN_XLIM[1]:.9g}}}",
                f"\\newcommand{{\\VerticalWLSZoomXMin}}{{{zoom_xlim[0]:.9g}}}",
                f"\\newcommand{{\\VerticalWLSZoomXMax}}{{{zoom_xlim[1]:.9g}}}",
                f"\\newcommand{{\\VerticalWLSZoomYMin}}{{{zoom_ylim[0]:.9g}}}",
                f"\\newcommand{{\\VerticalWLSZoomYMax}}{{{zoom_ylim[1]:.9g}}}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def weighted_linear_fit(x: np.ndarray, y: np.ndarray, bounds: np.ndarray) -> tuple[float, float]:
    bounds = np.maximum(bounds, 1e-12)
    weights = 1.0 / np.square(bounds)
    s = weights.sum()
    sx = (weights * x).sum()
    sy = (weights * y).sum()
    sxx = (weights * np.square(x)).sum()
    sxy = (weights * x * y).sum()
    delta = s * sxx - sx * sx
    if abs(delta) < 1e-18:
        return np.polyfit(x, y, deg=1)
    slope = (s * sxy - sx * sy) / delta
    intercept = (sxx * sy - sx * sxy) / delta
    return slope, intercept


def compute_vertical_bounds(points: np.ndarray, offsets: np.ndarray) -> np.ndarray:
    coords_eps = compute_coords_eps(points)
    z = points[:, 2]
    ranges_xy = calculate_range_xy(points)
    ranges = calculate_range(points)

    ranges_bound = coords_eps * np.sqrt(3.0)
    ranges_xy_bound = coords_eps * np.sqrt(2.0)
    phis_bound_num = ranges_xy_bound * np.abs(z) + coords_eps * ranges_xy
    phis_bound_den = np.square(ranges_xy) - ranges_xy_bound * ranges_xy
    correction_bound_num = np.abs(offsets) * ranges_bound
    correction_bound_den = np.square(ranges) - ranges_bound * ranges
    return phis_bound_num / phis_bound_den + correction_bound_num / correction_bound_den


def compute_coords_eps(points: np.ndarray) -> float:
    min_diff = np.inf
    for axis in range(3):
        values = np.sort(points[:, axis])
        positive_diffs = np.diff(values)[np.diff(values) > 0]
        if len(positive_diffs) > 0:
            min_diff = min(min_diff, positive_diffs.min())
    return max(min_diff / 2.0, 1e-6 / 2.0)


if __name__ == "__main__":
    main()
