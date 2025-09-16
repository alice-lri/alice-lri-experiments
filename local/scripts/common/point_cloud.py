import numpy as np

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

