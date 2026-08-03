#!/usr/bin/env python3
"""CARLA Python API 的薄适配层。

模块加载时不强制依赖 CARLA。只有真正连接模拟器或创建控制对象时才导入
``carla``，因此离线测试环境不会因为缺少 CARLA API 而失败。
"""

from __future__ import annotations

import importlib
import math
from typing import Any

from .waypoint_controller import ControlCommand


def require_carla() -> Any:
    """延迟导入 CARLA，并给出适合初学者定位问题的错误信息。"""
    try:
        return importlib.import_module("carla")
    except ImportError as exc:
        raise RuntimeError(
            "当前 Python 环境缺少 CARLA API。请安装与服务端一致的 "
            "carla==0.9.16。"
        ) from exc


def command_to_vehicle_control(command: ControlCommand) -> Any:
    """把项目控制命令转换成 ``carla.VehicleControl``。"""
    carla = require_carla()
    return carla.VehicleControl(
        throttle=float(command.throttle),
        steer=float(command.steer),
        brake=float(command.brake),
        hand_brake=False,
        reverse=False,
        manual_gear_shift=False,
    )


def velocity_to_speed_mps(velocity: Any) -> float:
    """把 CARLA 三维速度向量转换成标量速度，单位为 m/s。"""
    return math.sqrt(
        float(velocity.x) ** 2
        + float(velocity.y) ** 2
        + float(velocity.z) ** 2
    )
