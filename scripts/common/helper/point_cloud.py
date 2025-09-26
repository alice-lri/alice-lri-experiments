import numpy as np
#TODO fix all relative imports in python everywhere. probably use PYTHONPATH: take care of slurm tasks that use python

def load_binary(file_path):
    data = np.fromfile(file_path, dtype=np.float32)
    data = data.reshape((-1, 4))  # Assuming the format is x, y, z, intensity
    points = data[:, :3]
    intensity = data[:, 3]

    return points, intensity


def calculate_phi(points):
    distances_xy = np.sqrt(points[:, 0] ** 2 + points[:, 1] ** 2)
    return np.arctan2(points[:, 2], distances_xy)


def calculate_theta(points):
    points = np.array(points)
    return np.arctan2(points[:, 1], points[:, 0])


def calculate_range(points):
    return np.sqrt(points[:, 0] ** 2 + points[:, 1] ** 2 + points[:, 2] ** 2)


def calculate_range_xy(points):
    return np.sqrt(points[:, 0] ** 2 + points[:, 1] ** 2)


def calculate_xyz(phi, theta, r):
    x = r * np.cos(phi) * np.cos(theta)
    y = r * np.cos(phi) * np.sin(theta)
    z = r * np.sin(phi)

    return np.stack((x, y, z), axis=-1, dtype=np.float64)


def remove_outliers(points, max_coordinate=1000.0):
    points = np.array(points)
    mask = np.all(np.abs(points) <= max_coordinate, axis=1)

    return points[mask]
