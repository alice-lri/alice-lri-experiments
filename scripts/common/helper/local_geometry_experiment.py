import re
import time
from typing import Any

import numpy as np

from scripts.common.helper.local_geometry_metrics import symmetric_point_to_plane_metrics
from scripts.common.helper.ri.ri_default_mapper import RangeImageDefaultMapper
from scripts.common.helper.ri.ri_utils import point_cloud_to_range_image, range_image_to_point_cloud


DEFAULT_SEQUENCES = {
    "kitti": "2011_09_30_drive_0018_sync",
    "durlar": "DurLAR_20211209",
}

PBEA_SIZE_MULTIPLIERS = [1, 2, 4, 8, 16, 32]
PBEA_METHODS = ["pbea_native", *(f"pbea_x{multiplier}" for multiplier in PBEA_SIZE_MULTIPLIERS[1:])]
DEFAULT_METHODS = ["alice_lri", *PBEA_METHODS]

PBEA_NATIVE_RESOLUTIONS = {
    "kitti": (4000, 64),
    "durlar": (2048, 128),
}


def estimate_frame_relative_path(relative_path: str) -> str:
    estimate_path = re.sub(r"\d{10}\.bin$", "0000000000.bin", relative_path)
    if estimate_path == relative_path and not relative_path.endswith("0000000000.bin"):
        raise ValueError(f"Could not infer intrinsics-estimation frame from path: {relative_path}")

    return estimate_path


def estimate_intrinsics(alice_lri_module: Any, estimate_points):
    return alice_lri_module.estimate_intrinsics(
        estimate_points[:, 0],
        estimate_points[:, 1],
        estimate_points[:, 2],
    )


def evaluate_frame_methods(
    alice_lri_module: Any,
    dataset: str,
    original_points,
    intrinsics,
    methods: list[str],
    k_neighbors: int,
    base_fields: dict | None = None,
) -> list[dict]:
    rows = []
    base_fields = base_fields or {}

    if "alice_lri" in methods:
        start_time = time.perf_counter()
        reconstructed_points, ri_width, ri_height = reconstruct_alice_lri(
            alice_lri_module,
            intrinsics,
            original_points,
        )
        rows.append(
            build_metrics_row(
                base_fields=base_fields,
                method="alice_lri",
                ri_width=ri_width,
                ri_height=ri_height,
                original_points=original_points,
                reconstructed_points=reconstructed_points,
                k_neighbors=k_neighbors,
                runtime_seconds=time.perf_counter() - start_time,
            )
        )

    for method, ri_size_multiplier in iter_pbea_methods(methods):
        start_time = time.perf_counter()
        reconstructed_points, ri_width, ri_height = reconstruct_pbea(dataset, original_points, ri_size_multiplier)
        rows.append(
            build_metrics_row(
                base_fields=base_fields,
                method=method,
                ri_width=ri_width,
                ri_height=ri_height,
                original_points=original_points,
                reconstructed_points=reconstructed_points,
                k_neighbors=k_neighbors,
                runtime_seconds=time.perf_counter() - start_time,
            )
        )

    return rows


def iter_pbea_methods(methods: list[str]) -> list[tuple[str, int]]:
    methods_to_evaluate = []

    if "pbea_native" in methods:
        methods_to_evaluate.append(("pbea_native", 1))

    for method in methods:
        match = re.fullmatch(r"pbea_x(\d+)", method)
        if match:
            methods_to_evaluate.append((method, int(match.group(1))))

    return list(dict.fromkeys(methods_to_evaluate))


def reconstruct_alice_lri(alice_lri_module: Any, intrinsics, original_points):
    range_image = alice_lri_module.project_to_range_image(
        intrinsics,
        original_points[:, 0],
        original_points[:, 1],
        original_points[:, 2],
    )
    x, y, z = alice_lri_module.unproject_to_point_cloud(intrinsics, range_image)

    return np.column_stack((x, y, z)), range_image.width, range_image.height


def reconstruct_pbea(dataset: str, original_points, ri_size_multiplier: int = 1):
    ri_width, ri_height = PBEA_NATIVE_RESOLUTIONS[dataset]
    ri_width *= ri_size_multiplier
    ri_height *= ri_size_multiplier
    ri_mapper = RangeImageDefaultMapper(ri_width, ri_height)
    range_image = point_cloud_to_range_image(ri_mapper, original_points)
    reconstructed_points = range_image_to_point_cloud(ri_mapper, range_image)

    return reconstructed_points, ri_width, ri_height


def build_metrics_row(
    base_fields: dict,
    method: str,
    ri_width: int,
    ri_height: int,
    original_points,
    reconstructed_points,
    k_neighbors: int,
    runtime_seconds: float,
) -> dict:
    metrics_start_time = time.perf_counter()
    metrics = symmetric_point_to_plane_metrics(original_points, reconstructed_points, k_neighbors)
    metrics_runtime_seconds = time.perf_counter() - metrics_start_time

    return {
        **base_fields,
        "method": method,
        "ri_width": ri_width,
        "ri_height": ri_height,
        "original_points_count": len(original_points),
        "reconstructed_points_count": len(reconstructed_points),
        "k_neighbors": k_neighbors,
        "runtime_seconds": runtime_seconds + metrics_runtime_seconds,
        "metrics_runtime_seconds": metrics_runtime_seconds,
        **metrics,
    }
