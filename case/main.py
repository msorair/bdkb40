
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from build123d import *
from compounds.plate import build_plate_from_kle, PlateType
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
	plate = build_plate_from_kle(
		kle_data,
		unit_mm=d,
		margin_mm=margin,
		thickness_mm=thickness,
		switch_cutout_mm=switch_cutout_mm,
		switch_cutout_corner_radius_mm=switch_cutout_corner_radius_mm,
		stabilizer=kad_stabilizer,
		plate_type=PlateType.GASKET
	)
	show(plate, alphas=[0.3])
	# save to STL
	export_stl(plate, "keyboard_plate.stl")