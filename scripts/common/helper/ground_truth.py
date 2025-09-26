from scripts.common.helper.point_cloud import *

def compute_ground_truth(points, v_angles, v_offsets, h_offsets, h_resolutions, threshold=5e-4):
    assert np.all(np.diff(v_angles) > 0), "v_angles are not in ascending order"
    assert len(v_offsets) == len(v_angles), "v_offsets and v_angles have different lengths"

    phis = calculate_phi(points)
    thetas = calculate_theta(points)
    ranges = calculate_range(points)
    ranges_xy = calculate_range_xy(points)
    scanlines_ids = np.full(len(points), -1, dtype=int)
    theta_offsets = {}

    laser_idx = 0
    while laser_idx < len(v_offsets):
        v = v_offsets[laser_idx]
        phi_correction = np.arcsin(v / ranges)

        # find indices where correction was successful and phi is equal to the corresponding v_angle +- 1e-3
        idx = np.where(np.abs(phis - phi_correction - v_angles[laser_idx]) < threshold)[0]

        if len(idx) == 0:
            laser_idx += 1
            continue

        assert np.all(scanlines_ids[idx] == -1), "Some points were assigned to multiple scanlines"

        # assign scanline id to the corresponding indices
        scanlines_ids[idx] = laser_idx

        # compute diff to ideal and theta offset
        h = h_offsets[laser_idx]
        theta_step = 2 * np.pi / h_resolutions[laser_idx]
        corrected_thetas = thetas[idx] - np.arcsin(h / ranges_xy[idx])
        ideal_thetas = np.floor(corrected_thetas / theta_step) * theta_step
        theta_offsets[laser_idx] = float(np.mean(corrected_thetas - ideal_thetas))

        laser_idx += 1

    assert np.all(scanlines_ids != -1), "Some points were not assigned to any scanline"

    result = {
        'points_count': len(points),
        'scanlines_count': np.unique(scanlines_ids).shape[0],
        'scanlines': []
    }

    for laser_idx in np.unique(scanlines_ids):
        v_offset = v_offsets[laser_idx]
        v_angle = v_angles[laser_idx]
        h_offset = h_offsets[laser_idx]
        h_resolution = h_resolutions[laser_idx]

        points_count = int(np.sum(scanlines_ids == laser_idx))

        result['scanlines'].append({
            'laser_idx': int(laser_idx),
            'v_offset': v_offset,
            'v_angle': v_angle,
            'h_offset': h_offset,
            'h_resolution': h_resolution,
            'theta_offset': theta_offsets[laser_idx],
            'points_count': points_count
        })

    return scanlines_ids, result
