from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass

from build123d import *
from ocp_vscode import *
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
    top_h = 7.15 # 定位板到顶面的高度
    # 外形尺寸（x, y）
    outer_x = params.plate_width + 2 * params.wall_thickness + 2 * params.plate_margin
    outer_y = params.plate_length + 2 * params.wall_thickness + 2 * params.plate_margin 

    h = params.height

    outer = extrude(Plane.XY * Rectangle(outer_x, outer_y), amount=h)
    inner = extrude(Plane.XY * Rectangle(params.plate_width, params.plate_length), amount=h)


    top_sk = Rectangle(params.plate_width, params.plate_length).located(Location(Vector(0, 0, h))) - Rectangle(params.plate_width - params.plate_margin,  params.plate_length - params.plate_margin).located(Location(Vector(0, 0, h)))
    top_ex = extrude(Plane.XY * top_sk, amount=-params.wall_thickness)

    # 在 距离顶面 top_h 处放置定位板
    top_mount = outer - inner + top_ex
    if params.plate is not None:
        # plate_edge = top_mount.edges().filter_by(Axis.Z).sort_by(Axis.X)[0]
    
        plate_loc = Location(Vector(0, 0, h - top_h))
        top_mount += plate_loc * params.plate
    return top_mount


if __name__ == "__main__":
    params = TopMountParams(plate_length=234.6, plate_width=82.2, plate_margin=3.0, wall_thickness=1.5, height=19.65)
    top_mount_obj = make_top_mount(params)
    print("top_mount created with outer size:", params.plate_length + 2 * params.wall_thickness,
            params.plate_width + 2 * params.wall_thickness)
    show(top_mount_obj, alphas=[1])
