import argparse
import os
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import colormaps
from matplotlib.collections import LineCollection
from matplotlib.legend_handler import HandlerBase
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, ConnectionPatch, Rectangle

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
    DEFAULT_FRAME_ID = 150476
    ROBUST_POINT_COUNT_THRESHOLD = 64
    BAD_WLS_OFFSET_THRESHOLD_M = 0.05
    MAIN_XLIM = (0.0, 0.34)
    ZOOM_YLIM = (18.55, 21.7)
    ZOOM_X_PADDING = 0.0018
    OUTPUT_PATH = os.path.join(
        os.getenv("PAPER_FIGURES_DIR"),
        f"durlar_vertical_wls_fit_space_frame_{DEFAULT_FRAME_ID}_prototype.pdf",
    )


ESTIMATED_LINESTYLE = (0, (1.0, 1.6))
GT_LINESTYLE = "dashed"


class RainbowDot:
    pass


class HandlerRainbowDot(HandlerBase):
    def create_artists(self, legend, orig_handle, xdescent, ydescent, width, height, fontsize, trans):
        radius = min(width, height) * 0.40
        center_x = xdescent + width * 0.5
        center_y = ydescent + height * 0.5
        clip_circle = Circle((center_x, center_y), radius, transform=trans)
        artists = []
        cmap = colormaps["turbo"]
        stripe_count = 18
        stripe_width = (2 * radius) / stripe_count

        for i in range(stripe_count):
            stripe = Rectangle(
                (center_x - radius + i * stripe_width, center_y - radius),
                stripe_width,
                2 * radius,
                transform=trans,
                facecolor=cmap(i / (stripe_count - 1)),
                edgecolor="none",
            )
            stripe.set_clip_path(clip_circle)
            artists.append(stripe)

        artists.append(
            Circle(
                (center_x, center_y),
                radius,
                transform=trans,
                facecolor="none",
                edgecolor="0.35",
                linewidth=0.35,
            )
        )
        return artists


def main():
    parser = argparse.ArgumentParser(description="Generate the DurLAR sparse vertical-WLS failure figure.")
    parser.add_argument("--frame-id", type=int, default=Config.DEFAULT_FRAME_ID)
    parser.add_argument("--output", default=Config.OUTPUT_PATH)
    parser.add_argument(
        "--bad-offset-threshold-mm",
        type=float,
        default=Config.BAD_WLS_OFFSET_THRESHOLD_M * 1000.0,
        help="Threshold used to mark non-heuristic vertical-offset errors.",
    )
    args = parser.parse_args()

    frame = fetch_frame_case(args.frame_id)
    data = build_frame_data(frame)
    status = fetch_vertical_status(frame, args.bad_offset_threshold_mm / 1000.0)
    plot_vertical_wls_failure(frame, data, status, args.output)

    print(f"Figure written to {args.output}")


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
        "phi": phis,
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


def plot_vertical_wls_failure(frame: FrameCase, data: dict[str, np.ndarray], status: dict, output_path: str):
    zoom_xlim = compute_zoom_xlim(data, status)
    zoom_ylim = Config.ZOOM_YLIM

    fig = plt.figure(figsize=(7.0, 9.0), constrained_layout=True)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.15, 1.0])
    right_gs = gs[0, 1].subgridspec(
        5,
        1,
        height_ratios=[0.58, 1.20, 0.22, 0.72, 0.58],
    )

    main_ax = fig.add_subplot(gs[0, 0])
    zoom_ax = fig.add_subplot(right_gs[1, 0])
    legend_ax = fig.add_subplot(right_gs[3, 0])

    plot_frame(
        main_ax,
        frame,
        data,
        status,
        point_size=4.2,
        point_alpha=0.58,
        fit_linewidth=0.52,
        fit_alpha=0.60,
        line_x_range=Config.MAIN_XLIM,
        show_missing_gt=False,
        show_legend=False,
    )
    main_ax.set_xlim(*Config.MAIN_XLIM)
    main_ax.set_ylabel("$\\varphi$ (deg)")
    main_ax.set_title("Full Fitting Space", fontsize=10)
    add_zoom_box(main_ax, zoom_xlim, zoom_ylim)

    plot_frame(
        zoom_ax,
        frame,
        data,
        status,
        point_size=15.0,
        point_alpha=0.72,
        fit_linewidth=0.95,
        fit_alpha=0.72,
        line_x_range=zoom_xlim,
        show_gt_reference=True,
        show_missing_gt=False,
        points_zorder=4,
        line_zorder=2,
        show_legend=False,
    )
    zoom_ax.set_xlim(*zoom_xlim)
    zoom_ax.set_ylim(*zoom_ylim)
    zoom_ax.set_title("Problematic Scanlines", fontsize=10)
    zoom_ax.set_ylabel("")
    zoom_ax.tick_params(axis="both", labelsize=8)

    add_custom_legend(legend_ax)
    add_zoom_connectors(fig, main_ax, zoom_ax, zoom_xlim, zoom_ylim)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight", dpi=600)
    plt.close(fig)


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


def plot_frame(
    ax,
    frame: FrameCase,
    data: dict[str, np.ndarray],
    status: dict,
    point_size: float,
    point_alpha: float,
    fit_linewidth: float,
    fit_alpha: float,
    line_x_range: tuple[float, float],
    show_gt_reference: bool = False,
    show_missing_gt: bool = False,
    points_zorder: float | None = None,
    line_zorder: float | None = None,
    show_legend: bool = False,
):
    scanline_ids = data["scanline_ids"]
    unique_scanlines = np.unique(scanline_ids)
    colors = colormaps["turbo"](np.linspace(0.0, 1.0, max(unique_scanlines) + 1))

    ax.scatter(
        data["inv_range"],
        np.rad2deg(data["phi"]),
        c=colors[scanline_ids],
        s=point_size,
        alpha=point_alpha,
        edgecolors="0.20",
        linewidths=0.12,
        rasterized=True,
        zorder=points_zorder,
    )

    line_groups = {
        "gt_reference": [],
        "estimated": [],
        "fallback": [],
        "bad_wls": [],
        "missing": [],
    }
    counts = np.bincount(scanline_ids, minlength=int(unique_scanlines.max()) + 1)

    for scanline_idx in unique_scanlines:
        mask = scanline_ids == scanline_idx
        if mask.sum() < 1:
            continue

        xx = np.array(line_x_range)
        if show_gt_reference:
            yy = np.rad2deg(
                data["gt_vertical_offsets"][scanline_idx] * xx + data["gt_vertical_angles"][scanline_idx]
            )
            line_groups["gt_reference"].append(np.column_stack([xx, yy]))

        if scanline_idx in status["missing"]:
            if not show_missing_gt:
                continue
            slope = data["gt_vertical_offsets"][scanline_idx]
            intercept = data["gt_vertical_angles"][scanline_idx]
        elif int(scanline_idx) in status["estimated_lines"]:
            line = status["estimated_lines"][int(scanline_idx)]
            slope = line["vertical_offset"]
            intercept = line["vertical_angle"]
        elif mask.sum() >= 2:
            slope, intercept = weighted_linear_fit(data["inv_range"][mask], data["phi"][mask], data["bounds"][mask])
        else:
            continue

        yy = np.rad2deg(slope * xx + intercept)
        segment = np.column_stack([xx, yy])
        if scanline_idx in status["fallback"]:
            line_groups["fallback"].append(segment)
        elif scanline_idx in status["bad_wls"]:
            line_groups["bad_wls"].append(segment)
        elif scanline_idx in status["missing"]:
            line_groups["missing"].append(segment)
        elif counts[scanline_idx] >= Config.ROBUST_POINT_COUNT_THRESHOLD or mask.sum() >= 2:
            line_groups["estimated"].append(segment)

    add_line_collection(
        ax,
        line_groups["gt_reference"],
        color="#2f9e44",
        linewidth=fit_linewidth * 1.40,
        linestyle=GT_LINESTYLE,
        alpha=0.82,
        zorder=line_zorder,
    )
    add_line_collection(
        ax,
        line_groups["estimated"],
        color="black",
        linewidth=fit_linewidth,
        linestyle=ESTIMATED_LINESTYLE,
        alpha=fit_alpha,
        zorder=line_zorder,
    )
    add_line_collection(
        ax,
        line_groups["fallback"],
        color="#e68613",
        linewidth=fit_linewidth * 1.55,
        linestyle=ESTIMATED_LINESTYLE,
        alpha=0.95,
        zorder=line_zorder,
    )
    add_line_collection(
        ax,
        line_groups["bad_wls"],
        color="#7b2cbf",
        linewidth=fit_linewidth * 1.65,
        linestyle=ESTIMATED_LINESTYLE,
        alpha=0.96,
        zorder=line_zorder,
    )
    add_line_collection(
        ax,
        line_groups["missing"],
        color="#c1121f",
        linewidth=fit_linewidth,
        linestyle=ESTIMATED_LINESTYLE,
        alpha=0.45,
        zorder=line_zorder,
    )

    ax.set_xlabel("$1/r$ (m$^{-1}$)")
    ax.grid(True, alpha=0.25)

    if show_legend:
        add_custom_legend(ax)


def add_line_collection(ax, lines, color, linewidth, linestyle, alpha, zorder=None):
    ax.add_collection(
        LineCollection(
            lines,
            colors=color,
            linewidths=linewidth,
            linestyles=linestyle,
            alpha=alpha,
            zorder=zorder,
        )
    )


def add_custom_legend(ax):
    ax.axis("off")
    handles = [
        RainbowDot(),
        Line2D([0], [0], color="black", linestyle=ESTIMATED_LINESTYLE, linewidth=1.2),
        Line2D([0], [0], color="#2f9e44", linestyle=GT_LINESTYLE, linewidth=1.3),
        Line2D([0], [0], color="#e68613", linestyle=ESTIMATED_LINESTYLE, linewidth=1.6),
        Line2D([0], [0], color="#7b2cbf", linestyle=ESTIMATED_LINESTYLE, linewidth=1.7),
    ]
    labels = [
        "Observed Points",
        "Estimated Fit",
        "Ground-Truth Reference",
        "Heuristic Fallback",
        "Incorrectly Estimated Fit",
    ]
    ax.legend(
        handles,
        labels,
        loc="center left",
        frameon=False,
        fontsize=9,
        handlelength=2.6,
        handler_map={RainbowDot: HandlerRainbowDot()},
    )


def add_zoom_box(ax, xlim: tuple[float, float], ylim: tuple[float, float]):
    ax.add_patch(
        Rectangle(
            (xlim[0], ylim[0]),
            xlim[1] - xlim[0],
            ylim[1] - ylim[0],
            fill=False,
            edgecolor="0.2",
            linewidth=0.9,
            linestyle=(0, (3, 2)),
            alpha=0.9,
            zorder=10,
        )
    )


def add_zoom_connectors(fig, source_ax, target_ax, xlim: tuple[float, float], ylim: tuple[float, float]):
    for y in ylim:
        fig.add_artist(
            ConnectionPatch(
                xyA=(xlim[1], y),
                coordsA=source_ax.transData,
                xyB=(xlim[0], y),
                coordsB=target_ax.transData,
                color="0.22",
                linewidth=0.9,
                linestyle=(0, (2.2, 2.8)),
                alpha=0.62,
                zorder=1,
                clip_on=False,
            )
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
