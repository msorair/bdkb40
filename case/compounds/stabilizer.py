from __future__ import annotations

import json
import math
import numpy as np
import re
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from build123d import Polygon, Locations, Location, Align, Shape
from ocp_vscode import *

@dataclass(frozen=True)
class StabilizerScheme:
	"""Parametric stabilizer scheme.

	- `spacing_mm_by_u`: stabilizer insert center-to-center spacing for a given key size (in U).
	- `draw_cutout`: function that draws a single stabilizer cutout at the origin (inside a BuildSketch).
	- `min_u_exclusive`: apply stabilizer only when max(w_u, h_u) > this value.
	"""

	min_u_exclusive: float = 2.0
	spacing_mm_by_u = {
        2.25: 28.575,
        2.75: 28.575,
        3.0: 38.1,
        6.25: 100.0,
        7.0: 114.3,
    }

	def spacing_for_u(self, u: float) -> float | None:
		# Prefer exact key; otherwise tolerate common float noise
		if u in self.spacing_mm_by_u:
			return self.spacing_mm_by_u[u]
		for key_u, spacing in self.spacing_mm_by_u.items():
			if abs(key_u - u) < 1e-6:
				return spacing
		return None
	
	def draw_cutout(self, u, x, y) -> Shape:
		"""Draw a single stabilizer cutout at the origin (inside a BuildSketch)."""
		raise NotImplementedError("draw_cutout must be implemented by subclasses.")

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

class KadStabilizerScheme(StabilizerScheme):
	def __init__(self) -> None:
		#  i      j    ┌────────────┐
		#   \_┌──────┐ │      w     │ ┌──────┐
		#    ┌┘    k-│ │            │ │      └┐
		#   h│       └─┘            └─┘       │
		#    └┐       a      0,0             ┌┘
		#   / │-f    ┌─┐            ┌─┐      │
		#  g  │    b-│ │            │ │      │
		#     └─┐  ┌─┘ │            │ └─┐  ┌─┘
		#       └──┘ \ └────────────┘   └──┘ 
		#        |  \ c
		#        e   d
		self.w = 14.0
		y0 = -2.3
		a = 1.525
		b = 4.470
		c = 1.725
		d = 1.200
		e = 3.300
		f = 6.285
		g = 0.825
		h = 2.785
		i = 3.230
		j = 6.750
		k = 3.230

		pts_t = [
			[0, y0],
			[-a, y0],
			[-a, y0 - b],
			[-a - c, y0 - b],
			[-a - c, y0 - b - d],
			[-a - c - e, y0 - b - d],
			[-a - c - e, y0 - b],
			[-a - c - e - c, y0 - b],
			[-a - c - e - c, y0 - b + f],
			[-a - c - e - c - g, y0 - b + f],
			[-a - c - e - c - g, y0 - b + f + h],
			[-a - c - e - c, y0 - b + f + h],
			[-a - c - e - c, y0 - b + f + h + i],
			[-a - c - e - c + j, y0 - b + f + h + i],
			[-a - c - e - c + j, y0 - b + f + h + i - k],
			[- c - e - c + j, y0 - b + f + h + i - k],
		]
		self.template = pts_t
		super().__init__(
			min_u_exclusive=2.0,
		)

	def draw_cutout(self, u, x, y) -> Shape:
		lpts = np.array(self.template) - np.array([self.w / 2, 0])
		lpts = make_polygon_ccw(lpts)
		left_cutout = Polygon([tuple(pt) for pt in lpts.tolist()], align=Align.NONE)

		rpts = np.array(self.template) * np.array([-1, 1]) + np.array([self.w / 2, 0])
		rpts = make_polygon_ccw(rpts)
		right_cutout = Polygon([tuple(pt) for pt in rpts.tolist()], align=Align.NONE)
		# print(right_cutout.bounding_box())
		return Location((x, y, 0)) * left_cutout + Location((x, y, 0)) * right_cutout
		