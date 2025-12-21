from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from build123d import *
from ocp_vscode import *
from .stabilizer import KadStabilizerScheme, StabilizerScheme
from enum import IntEnum


class PlateType(IntEnum):
	DEFALT = 0
	GASKET = 1


@dataclass(frozen=True)
class KleKey:
	center_mm: tuple[float, float]
	size_mm: tuple[float, float]
	angle_deg: float


def _kle_to_json_str(kle: str) -> str:
	"""Convert the project's KLE fragment format into valid JSON.

	Expected input format in this repo:
	- Multiple row arrays separated by commas/newlines, WITHOUT an outermost wrapper.
	  Example:
	  ["q","w"],
	  [{w:1.25},"a"],
	- Dict keys may be unquoted (e.g. {w:1.25}).

	This function turns that into a valid JSON array of rows.
	"""
	s = kle.strip()
	# Remove JS-style comments (rare but seen in the wild)
	s = re.sub(r"//.*?$", "", s, flags=re.MULTILINE)
	s = re.sub(r"/\*.*?\*/", "", s, flags=re.DOTALL)
	# Quote object keys: {w:1} -> {"w":1}
	s = re.sub(r"([\{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', s)
	# Our repo uses KLE "rows" fragments without the outermost array.
	# Wrap them to form a JSON array of rows.
	s = re.sub(r",\s*$", "", s)
	s = f"[{s}]"
	return s


def _rot2d(x: float, y: float, deg: float, ox: float, oy: float) -> tuple[float, float]:
	if deg == 0:
		return x, y
	a = math.radians(deg)
	ca, sa = math.cos(a), math.sin(a)
	dx, dy = x - ox, y - oy
	return (ox + dx * ca - dy * sa, oy + dx * sa + dy * ca)


def parse_kle(
	kle: str,
	*,
	unit_mm: float = 19.05,
) -> list[KleKey]:
	"""Parse KLE layout (raw data) into a list of keys with mm geometry.

	Supported fields (common subset):
	- x, y: advance offsets (in units)
	- w, h: key width/height (in units)
	- r: rotation angle (deg)
	- rx, ry: rotation origin (in units)
	"""
	data: Any = json.loads(_kle_to_json_str(kle))
	if not isinstance(data, list):
		raise ValueError("KLE data must be a JSON array (rows)")

	keys: list[KleKey] = []

	# Cursor (top-left grid in KLE units)
	cur_x = 0.0
	cur_y = 0.0

	# Current key defaults
	cur_w = 1.0
	cur_h = 1.0

	# Rotation group (KLE semantics)
	rot_deg = 0.0
	rot_x = 0.0
	rot_y = 0.0

	def flush_key() -> None:
		nonlocal cur_x, cur_w, cur_h

		# Center in KLE units
		cx_u = cur_x + cur_w / 2.0
		cy_u = cur_y + cur_h / 2.0

		# Apply rotation around rotation origin (also in KLE units)
		cx_u, cy_u = _rot2d(cx_u, cy_u, rot_deg, rot_x, rot_y)

		# Convert to mm and flip Y (KLE down is +Y; CAD up is +Y)
		cx_mm = cx_u * unit_mm
		cy_mm = -cy_u * unit_mm
		w_mm = cur_w * unit_mm
		h_mm = cur_h * unit_mm

		keys.append(KleKey(center_mm=(cx_mm, cy_mm), size_mm=(w_mm, h_mm), angle_deg=rot_deg))

		# Advance cursor
		cur_x += cur_w

		# Reset per-key size defaults after placing a key
		cur_w = 1.0
		cur_h = 1.0

	for row in data:
		if not isinstance(row, list):
			raise ValueError("Each row must be a JSON array")

		cur_x = 0.0
		for token in row:
			if isinstance(token, dict):
				# Modifiers adjust state for upcoming keys
				if "x" in token:
					cur_x += float(token["x"])
				if "y" in token:
					cur_y += float(token["y"])

				if "w" in token:
					cur_w = float(token["w"])
				if "h" in token:
					cur_h = float(token["h"])

				if "r" in token:
					rot_deg = float(token["r"])
				if "rx" in token:
					rot_x = float(token["rx"])
				if "ry" in token:
					rot_y = float(token["ry"])

				continue

			# Key label; we don't need it for the plate but it indicates a key slot.
			if isinstance(token, (str, int, float)):
				flush_key()
				continue

			raise ValueError(f"Unsupported KLE token type: {type(token)}")

		# Next row
		cur_y += 1.0

	return keys


def _keys_bounds_mm(keys: Iterable[KleKey]) -> tuple[float, float, float, float]:
	xs: list[float] = []
	ys: list[float] = []
	for k in keys:
		cx, cy = k.center_mm
		w, h = k.size_mm
		# Conservative bounds: use the key rectangle corners and rotate around its center
		hw, hh = w / 2.0, h / 2.0
		corners = [
			(cx - hw, cy - hh),
			(cx + hw, cy - hh),
			(cx + hw, cy + hh),
			(cx - hw, cy + hh),
		]
		for x, y in corners:
			x2, y2 = _rot2d(x, y, k.angle_deg, cx, cy)
			xs.append(x2)
			ys.append(y2)
	if not xs or not ys:
		raise ValueError("No keys found in KLE data")
	return min(xs), min(ys), max(xs), max(ys)


def build_plate_from_kle(
	kle: str,
	*,
	unit_mm: float = 19.05,
	margin_mm: float = 3.0,
	thickness_mm: float = 1.5,
	switch_cutout_mm: float = 14.0,
	switch_cutout_corner_radius_mm: float = 0.5,
	stabilizer: StabilizerScheme | None = None,
	plate_type: PlateType = PlateType.DEFALT,
) -> Solid:
	keys = parse_kle(kle, unit_mm=unit_mm)
	min_x, min_y, max_x, max_y = _keys_bounds_mm(keys)
	print(f"Keys bounds mm: x[{min_x}, {max_x}], y[{min_y}, {max_y}]")
	plate_w = (max_x - min_x) + 2.0 * margin_mm
	plate_h = (max_y - min_y) + 2.0 * margin_mm
	plate_cx = (min_x + max_x) / 2.0
	plate_cy = (min_y + max_y) / 2.0

	# Base plate (algebra mode)
	plate_sk = Rectangle(plate_w, plate_h)
	plate = extrude(plate_sk, amount=thickness_mm)

	# Switch cutouts as a single sketch (algebra mode)
	holes_sk: Sketch | None = None
	for k in keys:
		cx, cy = k.center_mm
		# Recenter plate to origin by offsetting holes with -plate center
		lx = cx - plate_cx
		ly = cy - plate_cy
		hole = RectangleRounded(
			switch_cutout_mm,
			switch_cutout_mm,
			radius=switch_cutout_corner_radius_mm,
		)
		hole = Location((lx, ly, 0), (0, 0, k.angle_deg)) * hole
		holes_sk = hole if holes_sk is None else (holes_sk + hole)

		# # Stabilizers for keys larger than the threshold U
		# NOTE: When enabling this, prefer algebraic transforms (Location/Pos/Rot)
		# instead of `with Locations(...)` blocks.
		if stabilizer is not None:
			w_u = k.size_mm[0] / unit_mm
			h_u = k.size_mm[1] / unit_mm
			long_u = max(w_u, h_u)
			if long_u > stabilizer.min_u_exclusive:
				axis_rot = 0.0 if w_u >= h_u else 90.0
				stab_sk = stabilizer.draw_cutout(long_u, lx, ly)
				holes_sk += Location((0, 0, 0), (0, 0, axis_rot)) * stab_sk

	if holes_sk is not None:
		cutouts = extrude(Plane.XY * holes_sk, thickness_mm)
		plate -= cutouts
	
	edges = plate.edges().group_by(Axis.Z)[1]
	edges = edges.group_by(Axis.Y)[0] + edges.group_by(Axis.Y)[-1]
	plate = fillet(edges, 1)


	if plate_type == PlateType.GASKET:
		# mounting_sk_t = Rectangle(6, 6) + Circle(2.7)
		t = [
			(-7, -3),
			(-8, -2),
			(-8, 3),
			(-28, 3),
			(-28, 0.4),
			(-18, 0.4),
			(-18, -2),
			(-19, -3),
			(-7, -3),
		]
		mounting_sk_tc = Rectangle(6, 6) - Circle(2.7 / 2) + \
		                 Polygon([(-3, -3), (-3, -2), (-4, -3), (-3, -3)], align=Align.NONE) + \
						 Polygon([(3, -3), (4, -3), (3, -2), (3, -3)], align=Align.NONE)
		mounting_sk_tl = Polygon(t, align=Align.NONE)
		mounting_sk_tr = mirror(mounting_sk_tl, Plane.YZ)
		pos_list = [
			Pos(0, plate_h/2 + 3),
			Pos(plate_w/2 - 28 - 10, plate_h/2 + 3),
			Pos(-(plate_w/2 - 28 - 10), plate_h/2 + 3),
		]
		mounting_sk = Sketch()
		for pos in pos_list:
			mounting_sk += pos * mounting_sk_tc + pos * mounting_sk_tl + \
							pos * mounting_sk_tr
		mounting_sk += mirror(mounting_sk, Plane.XZ)
		mounting_cutouts = extrude(Plane.XY * mounting_sk, thickness_mm)
		edges = mounting_cutouts.edges().group_by(Axis.Z)[1]
		edges = edges.group_by(Axis.Y)[:2] + edges.group_by(Axis.Y)[-2:]
		mounting_cutouts = fillet(edges, 1)
		plate += mounting_cutouts
	return plate
