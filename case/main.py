from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from build123d import *
from ocp_vscode import *

from compounds.plate import PlateParameters, PlateType, build_plate_from_kle
from compounds.stabilizer import KadStabilizerScheme
from compounds.top_mount import TopMountParams, make_top_mount

kle_data = r"""
["esc","q","w","e","r","t","y","u","i","o","p","BS"],
[{w:1.25},"Caps","a","s","d","f","g","h","j","k","l",{w:1.75},"\\"],
[{w:1.75},"Shift","z","x","c","v","b","n","m",",",".",{w:1.25},"Shift"],
[{w:1.25},"Ctrl","Super",{w:1.25},"Alt",{w:2.25},"",{w:2.75},"",{w:1.25},"Fn","Super",{w:1.25},"Ctrl"]
"""


if __name__ == "__main__":
    d = 19.05
    margin = 3.0
    thickness = 1.5
    switch_cutout = 14.0
    switch_cutout_corner_radius = 0.5

    hole_radius = 2.7 / 2
    extra_holes = Sketch()
    extra_holes += Circle(hole_radius).move(Location(Vector(1.25*d, -d, 0)))
    extra_holes += Circle(hole_radius).move(Location(Vector(5.25*d, -d, 0)))
    extra_holes += Circle(hole_radius).move(Location(Vector(10.25*d, -d, 0)))
    extra_holes += Circle(hole_radius).move(Location(Vector(1.25*d, -3*d, 0)))
    extra_holes += Circle(hole_radius).move(Location(Vector(10.75*d, -3*d, 0)))
    extra_holes += Circle(hole_radius).move(Location(Vector(3.5*d, -3.5*d, 0)))
    extra_holes += Circle(hole_radius).move(Location(Vector(8.25*d, -3.5*d, 0)))

    kad_stabilizer = KadStabilizerScheme()
    plate, plate_parameters = build_plate_from_kle(
        kle_data,
        unit=d,
        margin=margin,
        thickness=thickness,
        switch_cutout=switch_cutout,
        switch_cutout_corner_radius=switch_cutout_corner_radius,
        stabilizer=kad_stabilizer,
        plate_type=PlateType.TOP_MOUNT,
        extra_holes=Sketch(extra_holes),
    )
    print("Plate parameters:", plate_parameters)
    # show(plate, alphas=[0.3])
    # save to STL
    export_stl(plate, "keyboard_plate.stl")

    # plate_parameters = PlateParameters(unit_mm=19.05, margin_mm=3.0, thickness_mm=1.5, switch_cutout_mm=14.0, switch_cutout_corner_radius_mm=0.5, stabilizer=KadStabilizerScheme(), plate_type=PlateType.GASKET, width_mm=234.60000000000002, length_mm=82.2, height_mm=1.5)
    top_mount_params = TopMountParams(
        plate_length=plate_parameters.length,
        plate_width=plate_parameters.width,
        plate_thickness=plate_parameters.thickness,
        plate_margin=plate_parameters.margin,
        wall_thickness=3,
        tilt_angle=4.77,
        height=19.65,
        plate=plate,
    )
    # top_mount = make_top_mount(top_mount_params)
    print(
        "Top mount created with outer size:",
        top_mount_params.plate_length
        + 2 * top_mount_params.wall_thickness
        + 2 * top_mount_params.plate_margin,
        top_mount_params.plate_width
        + 2 * top_mount_params.wall_thickness
        + 2 * top_mount_params.plate_margin,
    )
    show(plate)
