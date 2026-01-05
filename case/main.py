
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from build123d import *
from compounds.plate import build_plate_from_kle, PlateType, PlateParameters
from compounds.top_mount import TopMountParams, make_top_mount
from compounds.stabilizer import KadStabilizerScheme
from ocp_vscode import *

kle_data = r'''
["esc","q","w","e","r","t","y","u","i","o","p","BS"],
[{w:1.25},"Caps","a","s","d","f","g","h","j","k","l",{w:1.75},"\\"],
[{w:1.75},"Shift","z","x","c","v","b","n","m",",",".",{w:1.25},"Shift"],
[{w:1.25},"Ctrl","Super",{w:1.25},"Alt",{w:2.25},"",{w:2.75},"",{w:1.25},"Fn","Super",{w:1.25},"Ctrl"]
'''


if __name__ == "__main__":
	d = 19.05
	margin = 3.0
	thickness = 1.5
	switch_cutout_mm = 14.0
	switch_cutout_corner_radius_mm = 0.5

	kad_stabilizer = KadStabilizerScheme()
	plate, plate_parameters = build_plate_from_kle(
		kle_data,
		unit_mm=d,
		margin_mm=margin,
		thickness_mm=thickness,
		switch_cutout_mm=switch_cutout_mm,
		switch_cutout_corner_radius_mm=switch_cutout_corner_radius_mm,
		stabilizer=kad_stabilizer,
		plate_type=PlateType.TOP_MOUNT
	)
	# print("Plate parameters:", plate_parameters)
	# show(plate, alphas=[0.3])
	# save to STL
	# export_stl(plate, "keyboard_plate.stl")

	# plate_parameters = PlateParameters(unit_mm=19.05, margin_mm=3.0, thickness_mm=1.5, switch_cutout_mm=14.0, switch_cutout_corner_radius_mm=0.5, stabilizer=KadStabilizerScheme(), plate_type=PlateType.GASKET, width_mm=234.60000000000002, length_mm=82.2, height_mm=1.5)
	top_mount_params = TopMountParams(plate_length=plate_parameters.length_mm, plate_width=plate_parameters.width_mm, plate_margin=plate_parameters.margin_mm, wall_thickness=3, height=19.65, plate=plate)
	top_mount = make_top_mount(top_mount_params)
	print("Top mount created with outer size:", top_mount_params.plate_length + 2 * top_mount_params.wall_thickness + 2 * top_mount_params.plate_margin,
			top_mount_params.plate_width + 2 * top_mount_params.wall_thickness + 2 * top_mount_params.plate_margin)
	show(top_mount, alphas=[1])
	