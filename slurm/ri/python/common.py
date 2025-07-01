import numpy as np
from ri_mapper import RangeImageMapper


def load_binary(file_path):
    data = np.fromfile(file_path, dtype=np.float32)
    data = data.reshape((-1, 4))
    points = data[:, :3]
    intensity = data[:, 3]

    mask = calculate_range(points) > 0

    return points[mask], intensity[mask]

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


def point_cloud_to_range_image(ri_mapper: RangeImageMapper, points, intensities=None):
    r = calculate_range(points)
    theta, phi = ri_mapper.map(points)

    range_image = np.full((ri_mapper.h, ri_mapper.w), -1.0, dtype=np.float32)
    range_image[phi, theta] = r

    if intensities is not None:
        intensity_image = np.full((ri_mapper.h, ri_mapper.w), -1.0, dtype=np.float32)
        intensity_image[phi, theta] = intensities * 255

        return range_image, intensity_image

    return range_image


def range_image_to_point_cloud(ri_mapper: RangeImageMapper, range_image):
    theta, phi = ri_mapper.unmap()
    r = range_image.flatten()

    valid = r > 0
    phi = phi[valid]
    theta = theta[valid]
    r = r[valid]

    points = calculate_xyz(phi, theta, r)

    return points