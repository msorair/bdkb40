from __future__ import annotations

import json
import math
import re
import numpy as np
from dataclasses import dataclass

from build123d import (
    Part,
    Polygon,
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
    Compound,
    Shape,
    Sketch,
    Align,
    Rot,
)
from ocp_vscode import show_all, show_object, show
from enum import IntEnum
import typing

from utility.geometry import make_polygon_ccw


@dataclass
class TopMountParams:
    """Parameters for generating a top_mount-style keyboard shell.

    plate_length: 定位板长度 (x 方向)
    plate_width: 定位板宽度 (y 方向)
    plate_margin: 按键到定位板边缘的距离
    wall_thickness: 外壳壁厚
    tilt_angle: 倾斜角度
    height: 壁高（不含底面/顶面）
    """

    plate_length: float
    plate_width: float
    plate_thickness: float
    plate_margin: float
    wall_thickness: float
    tilt_angle: float
    height: float
    plate: typing.Any = None


def make_top_mount(params: TopMountParams):
    """生成 top_mount 结构"""
    heatset: list[float] = [2, 3, 3.5]  # 螺丝孔直径，热嵌套孔深度，热嵌套孔直径
    screw: list[float] = [2, 4, 2, 3.6]  # 螺丝直径，螺杆长度，头部高度，头部直径
    # outer_fillet_r = 3  # 外角圆角半径
    fillet_r = 2  # 圆角半径
    outer_y_padding = 1  # y 方向外形额外增加的尺寸
    btm_thickness = 3  # 底板厚度
    # tolerance_1 = 0.5   # 公差1
    tolerance_2 = 0.2  # 公差2
    tolerance_3 = 0.5  # 公差3
    top_h = params.height - btm_thickness  # 顶盖高度
    top_to_plate_h = 7.15  # 定位板到顶面的高度

    # 外形尺寸（x, y）
    outer_x = params.plate_length + 2 * (params.wall_thickness)
    outer_y = params.plate_width + 2 * (params.wall_thickness + outer_y_padding)
    inner_x = params.plate_length - params.plate_margin + 2
    inner_y = params.plate_width - params.plate_margin + 2
    inner_y_padding = -1

    left_pts_t1: np.ndarray = np.array(
        [
            [0, 0],
            [-outer_y, 0],
            [-outer_y, top_h],
            [0, top_h + math.tan(math.radians(params.tilt_angle)) * outer_y],
            [0, 0],
        ]
    )
    hp = math.tan(math.radians(params.tilt_angle)) * (
        params.wall_thickness + outer_y_padding - inner_y_padding
    )
    left_pts_t2: np.ndarray = np.array(
        [
            [0, 0],
            [-(inner_y + 2*inner_y_padding), 0],
            [-(inner_y + 2*inner_y_padding), top_h + hp],
            [
                0,
                top_h
                + math.tan(math.radians(params.tilt_angle))
                * (inner_y + 2*inner_y_padding)
                + hp,
            ],
            [0, 0],
        ]
    )

    left_sk1 = Polygon(
        [tuple(pt) for pt in make_polygon_ccw(left_pts_t1).tolist()], align=Align.NONE
    )
    left_sk2 = Polygon(
        [tuple(pt) for pt in make_polygon_ccw(left_pts_t2).tolist()], align=Align.NONE
    )

    outer = extrude(typing.cast(Sketch, Plane.YZ * left_sk1), amount=outer_x)
    outer_edge_groups = outer.edges().group_by(Axis.Z)
    outer = fillet(outer_edge_groups[1] + outer_edge_groups[2], fillet_r)
    outer_edge_groups = outer.edges().group_by(Axis.Z)
    outer = fillet(outer_edge_groups[-1] + outer_edge_groups[-2] + outer_edge_groups[-3], fillet_r)

    inner = extrude(typing.cast(Sketch, Plane.YZ * left_sk2), amount=inner_x)
    inner_edge_groups = inner.edges().group_by(Axis.Z)
    inner = fillet(inner_edge_groups[1] + inner_edge_groups[2], fillet_r)
    top_mount_p1 = outer - inner.move(
        Location(
            Vector(params.wall_thickness, -params.wall_thickness - outer_y_padding + inner_y_padding, 0)
        )
    )
    top_face = top_mount_p1.faces().group_by(Axis.Z)[-3][0]
    top_sk1 = RectangleRounded(inner_y, inner_x, fillet_r) - RectangleRounded(        
        params.plate_width - 2 * params.plate_margin,
        params.plate_length - 2 * params.plate_margin,
        1
    )
    # top_sk1 = top_sk1.move(Location(Vector(-2.15, 0, 0)))
    top_ex1 = extrude(
        typing.cast(Sketch, Plane(top_face) * top_sk1),
        amount=-params.wall_thickness,
    )
    # top_mount_p1 += top_ex1
    top_ex1_face = top_mount_p1.faces().group_by(Axis.Z)[-1]
    top_ex_inner_edges = top_ex1_face.edges().group_by(Axis.X)[1:-1]  # type: ignore
    # top_mount_p1 = fillet(top_ex_inner_edges, 0.5)
    top_mount_p1.locate(Location(Vector(-outer_x / 2, outer_y / 2, 0)))

    # 在 距离顶面 top_h 处放置定位板
    if params.plate is not None:
        plate_loc = Location(Vector(0, 0.3765, top_h - top_to_plate_h - math.cos(math.radians(params.tilt_angle)) * params.plate_thickness + math.tan(math.radians(params.tilt_angle)) * (
        (outer_y) / 2
    )))
        # rot_axis =
        top_mount_p1 += plate_loc * Rot(X=params.tilt_angle) * params.plate



    # # 底面 四个角 M2.5 螺丝孔，距离外侧边缘 2.25 mm
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
        typing.cast(Sketch, Plane.XY * heatset_hole_sk), amount=heatset[1] * 1.5
    )

    top_mount_p1 = top_mount_p1 - heatset_holes

    inner_2_x = outer_x - 2
    inner_2_y = outer_y - 2
    btm_w_sk = RectangleRounded(outer_x, outer_y, fillet_r) - RectangleRounded(
        inner_2_x, inner_2_y, fillet_r
    )
    # top_mount_p1 = top_mount_p1 + extrude(typing.cast(Sketch, Plane.XY * btm_w_sk), amount=-(btm_thickness + tolerance_2))

    # 底板
    outer_btm_sk = RectangleRounded(
        inner_2_x - tolerance_2, inner_2_y - tolerance_2, fillet_r
    )
    top_mount_p2 = extrude(
        typing.cast(Sketch, Plane.XY * outer_btm_sk), amount=btm_thickness
    )
    p2_hole_sk1 = Circle((screw[0] + tolerance_2) / 2)

    p2_holes1 = hole_locations * extrude(
        typing.cast(
            Sketch, Plane(top_mount_p2.faces().sort_by(Axis.Z)[-1]) * p2_hole_sk1
        ),
        amount=-tolerance_3,
    )

    p2_hole_sk2 = Circle((screw[3] + tolerance_2) / 2)
    p2_holes2 = hole_locations * extrude(
        typing.cast(
            Sketch, Plane(top_mount_p2.faces().sort_by(Axis.Z)[0]) * p2_hole_sk2
        ),
        amount=-(btm_thickness - tolerance_3),
    )
    top_mount_p2 = top_mount_p2 - p2_holes1 - p2_holes2
    top_mount_p2 = top_mount_p2.located(
        Location(Vector(0, 0, -btm_thickness - tolerance_2))
    )
    return top_mount_p1, top_mount_p2


if __name__ == "__main__":
    params = TopMountParams(
        plate_length=234.6,
        plate_width=82.2,
        plate_thickness=1.5,
        plate_margin=3.0,
        wall_thickness=1.5,
        tilt_angle=5,
        height=19.65,
    )
    top_mount_obj = make_top_mount(params)
    print(
        "top_mount created with outer size:",
        params.plate_length + 2 * params.wall_thickness,
        params.plate_width + 2 * params.wall_thickness,
    )
    show(top_mount_obj, alphas=[1])
