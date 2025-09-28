from scripts.common.helper.ri.ri_mapper import *
from scripts.common.helper.point_cloud import *


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