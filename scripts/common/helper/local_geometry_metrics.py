from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.neighbors import NearestNeighbors


@dataclass(frozen=True)
class DirectionalPointToPlaneResult:
    errors: np.ndarray
    nn_indices: np.ndarray


def estimate_normals_pca(points: np.ndarray, k_neighbors: int = 12) -> np.ndarray:
    points = _as_points(points)
    _validate_k_neighbors(k_neighbors)

    if len(points) < 3:
        raise ValueError("At least 3 points are required to estimate local planes.")

    neighbor_count = min(k_neighbors, len(points))
    neighbors = NearestNeighbors(n_neighbors=neighbor_count, algorithm="auto")
    neighbors.fit(points)
    _, neighbor_indices = neighbors.kneighbors(points, return_distance=True)

    neighborhoods = points[neighbor_indices]
    centered = neighborhoods - neighborhoods.mean(axis=1, keepdims=True)
    covariances = np.einsum("nki,nkj->nij", centered, centered) / neighbor_count

    _, eigenvectors = np.linalg.eigh(covariances)
    normals = eigenvectors[:, :, 0]
    norms = np.linalg.norm(normals, axis=1, keepdims=True)

    return normals / np.maximum(norms, np.finfo(np.float64).eps)


def directional_point_to_plane_errors(
    query_points: np.ndarray,
    reference_points: np.ndarray,
    reference_normals: np.ndarray,
) -> DirectionalPointToPlaneResult:
    query_points = _as_points(query_points)
    reference_points = _as_points(reference_points)
    reference_normals = _as_points(reference_normals)

    if len(query_points) == 0 or len(reference_points) == 0:
        return DirectionalPointToPlaneResult(np.array([], dtype=np.float64), np.array([], dtype=np.int64))

    if len(reference_points) != len(reference_normals):
        raise ValueError("reference_points and reference_normals must contain the same number of rows.")

    neighbors = NearestNeighbors(n_neighbors=1, algorithm="auto")
    neighbors.fit(reference_points)
    _, nn_indices = neighbors.kneighbors(query_points, return_distance=True)
    nn_indices = nn_indices[:, 0]

    deltas = query_points - reference_points[nn_indices]
    errors = np.abs(np.einsum("ij,ij->i", deltas, reference_normals[nn_indices]))

    return DirectionalPointToPlaneResult(errors=errors, nn_indices=nn_indices)


def symmetric_point_to_plane_metrics(
    original_points: np.ndarray,
    reconstructed_points: np.ndarray,
    k_neighbors: int = 12,
) -> dict[str, float]:
    original_points = _as_points(original_points)
    reconstructed_points = _as_points(reconstructed_points)
    _validate_k_neighbors(k_neighbors)

    original_normals = estimate_normals_pca(original_points, k_neighbors)
    reconstructed_normals = estimate_normals_pca(reconstructed_points, k_neighbors)

    reconstructed_to_original = directional_point_to_plane_errors(
        query_points=reconstructed_points,
        reference_points=original_points,
        reference_normals=original_normals,
    ).errors
    original_to_reconstructed = directional_point_to_plane_errors(
        query_points=original_points,
        reference_points=reconstructed_points,
        reference_normals=reconstructed_normals,
    ).errors

    symmetric_errors = np.concatenate([reconstructed_to_original, original_to_reconstructed])

    return {
        **_prefixed_stats("reconstructed_to_original_point_to_plane", reconstructed_to_original),
        **_prefixed_stats("original_to_reconstructed_point_to_plane", original_to_reconstructed),
        **_prefixed_stats("point_to_plane", symmetric_errors),
    }


def _prefixed_stats(prefix: str, errors: np.ndarray) -> dict[str, float]:
    if len(errors) == 0:
        return {
            f"{prefix}_mean": np.nan,
            f"{prefix}_rmse": np.nan,
            f"{prefix}_median": np.nan,
            f"{prefix}_p95": np.nan,
            f"{prefix}_max": np.nan,
        }

    return {
        f"{prefix}_mean": float(np.mean(errors)),
        f"{prefix}_rmse": float(np.sqrt(np.mean(np.square(errors)))),
        f"{prefix}_median": float(np.median(errors)),
        f"{prefix}_p95": float(np.percentile(errors, 95)),
        f"{prefix}_max": float(np.max(errors)),
    }


def _as_points(points: np.ndarray) -> np.ndarray:
    points = np.asarray(points, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError(f"Expected an array with shape (n, 3), got {points.shape}.")
    return points


def _validate_k_neighbors(k_neighbors: int):
    if k_neighbors < 3:
        raise ValueError("k_neighbors must be at least 3.")
