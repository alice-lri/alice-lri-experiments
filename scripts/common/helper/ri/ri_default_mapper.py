from common.helper.point_cloud import *
from common.helper.ri.ri_mapper import *

class RangeImageDefaultMapper(RangeImageMapper):

    def __init__(self, w, h):
        super().__init__(w, h)
        self.min_phi = 0
        self.max_phi = 0

    def map(self, points):
        theta = calculate_theta(points)
        phi = calculate_phi(points)

        theta = (theta + np.pi) / (2 * np.pi) * (self.w - 1)

        self.min_phi, self.max_phi = np.min(phi), np.max(phi)
        phi = (phi - self.min_phi) / (self.max_phi - self.min_phi) * (self.h - 1)

        theta = np.clip(np.round(theta).astype(np.int32), 0, self.w - 1)
        phi = np.clip(np.round(phi).astype(np.int32), 0, self.h - 1)

        return theta, phi

    def unmap(self):
        theta_indices = np.linspace(-np.pi, np.pi, self.w, endpoint=True)
        phi_indices = np.linspace(self.min_phi, self.max_phi, self.h, endpoint=True)

        theta, phi = np.meshgrid(theta_indices, phi_indices)

        return theta.flatten(), phi.flatten()
