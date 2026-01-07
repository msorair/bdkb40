from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass

from build123d import (
    Rectangle,
    Circle,
    Locations,
    Location,
    RectangleRounded,
    Plane,
    Axis,
    Vector,
    extrude,
    fillet,
)
from ocp_vscode import show_all, show_object, show
from enum import IntEnum
import typing


@dataclass
class TopMountParams:
    """Parameters for generating a top_mount-style keyboard shell.

    plate_length: 定位板长度 (x 方向)
    plate_width: 定位板宽度 (y 方向)
    plate_margin: 按键到定位板边缘的距离
    wall_thickness: 外壳壁厚
    height: 壁高（不含底面/顶面）
    """

    plate_length: float
    plate_width: float
    plate_margin: float
    wall_thickness: float
    height: float
    plate: typing.Any = None


def make_top_mount(params: TopMountParams):
    """生成 top_mount 结构（四周壁，无顶无底）。

    返回一个 Build123d 对象（组合体），位于 XY 平面原点中心。
    内腔尺寸 = 定位板尺寸
    外形尺寸 = 内腔尺寸 + 2 * wall_thickness + 2 * plate_margin
    """
    top_h = 7.15  # 定位板到顶面的高度
    # 外形尺寸（x, y）
    outer_x = params.plate_width + 2 * params.wall_thickness
    outer_y = params.plate_length + 2 * params.wall_thickness + 6

    inner_x = params.plate_width - 1
    inner_y = params.plate_length - 1

    h = params.height

    outer = extrude(Plane.XY * RectangleRounded(outer_x, outer_y, 3), amount=h)
    inner = extrude(Plane.XY * RectangleRounded(inner_x, inner_y, 2), amount=h)

    top_sk1 = Rectangle(inner_x, inner_y + 1).located(
        Location(Vector(0, 0, h))
    ) - RectangleRounded(
        params.plate_width - 2 * params.plate_margin - 1,
        params.plate_length - 2 * params.plate_margin - 1,
        1,
    ).located(Location(Vector(0, 0, h)))
    top_ex1 = extrude(Plane.XY * top_sk1, amount=-params.wall_thickness)
    top_ex1_face = top_ex1.faces().group_by(Axis.Z)[-1]
    top_innet_edges = top_ex1_face.edges().group_by(Axis.X)[1:-1]
    top_ex1 = fillet(top_innet_edges, 0.5)

    # 在 距离顶面 top_h 处放置定位板
    top_mount = outer - inner + top_ex1
    if params.plate is not None:
        plate_loc = Location(Vector(0, 0, h - top_h))
        top_mount += plate_loc * params.plate

    top_face = top_mount.faces().group_by(Axis.Z)[-1]
    top_edges_y0 = (
        top_face.edges().group_by(Axis.Y)[0] + top_face.edges().group_by(Axis.Y)[-1]
    )
    top_mount = fillet(top_edges_y0, 2.5)

    # 底面 四个角 M2.5 螺丝孔，距离外侧边缘 2.25 mm
    heatset = [2.5, 3, 3.5]  # 螺丝孔直径，热嵌套孔深度，热嵌套孔直径
    hole_x = (outer_x / 2) - 2.25 - heatset[2] / 2
    hole_y = (outer_y / 2) - 2.25 - heatset[2] / 2
    hole_locations = Locations(
        [
            Location(Vector(hole_x, hole_y, 0)),
            Location(Vector(-hole_x, hole_y, 0)),
            Location(Vector(-hole_x, -hole_y, 0)),
            Location(Vector(hole_x, -hole_y, 0)),
        ]
    )
    heatset_hole_sk = Circle(heatset[2] / 2)
    heatset_holes = hole_locations * extrude(
        Plane.XY * heatset_hole_sk, amount=heatset[1] * 1.5
    )

    # screw_hole_sk = Circle(heatset[0] / 2)
    # screw_holes = hole_locations * extrude(Plane.XY * screw_hole_sk, amount=h)

    top_mount = top_mount - heatset_holes

    inner_2_x = outer_x - 2
    inner_2_y = outer_y - 2
    btm_w_sk = RectangleRounded(outer_x, outer_y, 3) - RectangleRounded(
        inner_2_x, inner_2_y, 2
    )
    top_mount += extrude(Plane.XY * btm_w_sk, amount=-2)

    return top_mount


if __name__ == "__main__":
    params = TopMountParams(
        plate_length=234.6,
        plate_width=82.2,
        plate_margin=3.0,
        wall_thickness=1.5,
        height=19.65,
    )
    top_mount_obj = make_top_mount(params)
    print(
        "top_mount created with outer size:",
        params.plate_length + 2 * params.wall_thickness,
        params.plate_width + 2 * params.wall_thickness,
    )
    show(top_mount_obj, alphas=[1])
