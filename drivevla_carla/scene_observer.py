#!/usr/bin/env python3
"""把 CARLA 真值状态整理成 DriveVLA 在线 prompt 所需字段。"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from typing import Any

from .carla_adapter import velocity_to_speed_mps
from .prompt_builder import EgoMotion, NearbyActor, SceneStats


@dataclass(frozen=True)
class MotionSample:
    """一帧 ego 位姿和速度历史。"""

    timestamp_s: float
    x: float
    y: float
    yaw_deg: float
    speed_mps: float


def normalize_angle_deg(angle_deg: float) -> float:
    """把角度归一化到 [-180, 180) 范围。"""
    return (angle_deg + 180.0) % 360.0 - 180.0


def world_delta_to_ego(
    dx: float,
    dy: float,
    ego_yaw_deg: float,
) -> tuple[float, float]:
    """把 CARLA 世界坐标差转换为前向为 x、左向为 y 的 ego 坐标。"""
    yaw = math.radians(ego_yaw_deg)
    forward = dx * math.cos(yaw) + dy * math.sin(yaw)
    # CARLA 局部 y 轴向右，训练轨迹的 lateral 正方向向左，因此这里取反。
    lateral = dx * math.sin(yaw) - dy * math.cos(yaw)
    return forward, lateral


class SceneObserver:
    """维护 ego 历史，并从 CARLA actor 真值生成场景摘要。"""

    def __init__(self, history_duration_s: float = 1.5, nearby_radius_m: float = 50.0) -> None:
        self.history_duration_s = history_duration_s
        self.nearby_radius_m = nearby_radius_m
        self._history: deque[MotionSample] = deque()

    def update(self, ego_vehicle: Any, timestamp_s: float) -> None:
        """记录当前 ego 状态，并删除超过历史窗口的旧样本。"""
        transform = ego_vehicle.get_transform()
        sample = MotionSample(
            timestamp_s=float(timestamp_s),
            x=float(transform.location.x),
            y=float(transform.location.y),
            yaw_deg=float(transform.rotation.yaw),
            speed_mps=velocity_to_speed_mps(ego_vehicle.get_velocity()),
        )
        self._history.append(sample)
        cutoff = sample.timestamp_s - self.history_duration_s
        while len(self._history) > 1 and self._history[0].timestamp_s < cutoff:
            self._history.popleft()

    def ego_motion(self) -> EgoMotion:
        """按照 v5 prompt 字段输出最近运动摘要。"""
        if not self._history:
            return EgoMotion(0, 0.0, [], 0.0, 0.0, 0.0, 0.0, 0.0)
        first = self._history[0]
        last = self._history[-1]
        duration = max(last.timestamp_s - first.timestamp_s, 0.0)
        accel = (last.speed_mps - first.speed_mps) / max(duration, 1e-6)
        forward, lateral = world_delta_to_ego(
            last.x - first.x,
            last.y - first.y,
            first.yaw_deg,
        )
        # 只采样最多 4 个速度值，避免 20 Hz 历史让 prompt 变长。
        samples = list(self._history)
        stride = max(1, math.ceil(len(samples) / 4))
        speeds = [sample.speed_mps for sample in samples[::stride]][-4:]
        return EgoMotion(
            history_steps=len(samples),
            history_duration_s=duration,
            history_speed_mps=speeds,
            current_speed_mps=last.speed_mps,
            history_accel_mps2=accel,
            history_yaw_delta_deg=normalize_angle_deg(last.yaw_deg - first.yaw_deg),
            history_forward_delta_m=forward,
            history_lateral_delta_m=lateral,
        )

    def observe_actors(self, world: Any, ego_vehicle: Any) -> tuple[SceneStats, list[NearbyActor]]:
        """读取附近车辆和行人；这些字段属于模拟器真值弱监督。"""
        ego_transform = ego_vehicle.get_transform()
        ego_location = ego_transform.location
        nearby: list[NearbyActor] = []
        vehicle_count = 0
        pedestrian_count = 0

        for actor in world.get_actors():
            if actor.id == ego_vehicle.id:
                continue
            type_id = str(actor.type_id)
            if type_id.startswith("vehicle."):
                category = "vehicle"
            elif type_id.startswith("walker.pedestrian."):
                category = "pedestrian"
            else:
                continue
            location = actor.get_location()
            dx = float(location.x - ego_location.x)
            dy = float(location.y - ego_location.y)
            distance = math.hypot(dx, dy)
            if distance > self.nearby_radius_m:
                continue
            forward, lateral = world_delta_to_ego(dx, dy, ego_transform.rotation.yaw)
            nearby.append(NearbyActor(category, distance, forward, lateral))
            if category == "vehicle":
                vehicle_count += 1
            else:
                pedestrian_count += 1

        return SceneStats(vehicle_count, pedestrian_count, 0), nearby
