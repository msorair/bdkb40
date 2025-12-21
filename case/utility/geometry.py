import numpy as np

def make_polygon_cw(polygon, epsilon=1e-10):
    polygon = np.asarray(polygon, dtype=np.float64)
    if polygon.shape[0] < 3 or polygon.ndim != 2:
        return polygon
    x = polygon[:, 0]
    y = polygon[:, 1]
    signed_area = 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)
    if abs(signed_area) < epsilon:
        return polygon
    return polygon[::-1].copy() if signed_area > 0 else polygon.copy()

def make_polygon_ccw(polygon, epsilon=1e-10):
    polygon = np.asarray(polygon, dtype=np.float64)
    if polygon.shape[0] < 3 or polygon.ndim != 2:
        return polygon
    x = polygon[:, 0]
    y = polygon[:, 1]
    signed_area = 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)
    if abs(signed_area) < epsilon:
        return polygon
    return polygon[::-1].copy() if signed_area < 0 else polygon.copy()
