#!/usr/bin/env python3
"""构造 CARLA 车道中心路线，并计算闭环行驶进度。"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Sequence

from .scene_observer import normalize_angle_deg


@dataclass(frozen=True)
class RoutePoint:
    """不依赖 CARLA 类型的路线采样点。"""

    x: float
    y: float
    z: float
    yaw_deg: float
    distance_m: float
    is_junction: bool = False


def choose_branch(candidates: Sequence[Any], current_yaw: float, command: str) -> Any:
    """按照 CARLA 右手坐标系选择直行、左转或右转分支。"""
    command = command.upper()
    scored = [
        (
            normalize_angle_deg(float(item.transform.rotation.yaw) - current_yaw),
            item,
        )
        for item in candidates
    ]
    if command == "LEFT":
        # CARLA 局部 y 指向右侧，因此负航向变化对应左转。
        return min(scored, key=lambda pair: pair[0])[1]
    if command == "RIGHT":
        return max(scored, key=lambda pair: pair[0])[1]
    if command != "STRAIGHT":
        raise ValueError("route_command 只能是 STRAIGHT、LEFT 或 RIGHT")
    return min(scored, key=lambda pair: abs(pair[0]))[1]


def build_lane_route(
    carla_map: Any,
    start_location: Any,
    route_length_m: float,
    step_m: float = 2.0,
    route_command: str = "STRAIGHT",
) -> list[RoutePoint]:
    """从出生点沿当前车道向前采样一条确定性路线。"""
    waypoint = carla_map.get_waypoint(start_location)
    if waypoint is None:
        raise RuntimeError("ego 出生点无法投影到 CARLA 车道")
    route: list[RoutePoint] = []
    cumulative = 0.0
    previous_location = waypoint.transform.location
    while cumulative <= route_length_m:
        transform = waypoint.transform
        location = transform.location
        route.append(
            RoutePoint(
                float(location.x),
                float(location.y),
                float(location.z),
                float(transform.rotation.yaw),
                cumulative,
                bool(waypoint.is_junction),
            )
        )
        candidates = waypoint.next(step_m)
        if not candidates:
            break
        current_yaw = float(transform.rotation.yaw)
        waypoint = choose_branch(candidates, current_yaw, route_command)
        next_location = waypoint.transform.location
        cumulative += math.hypot(
            float(next_location.x - previous_location.x),
            float(next_location.y - previous_location.y),
        )
        previous_location = next_location
    if len(route) < 2:
        raise RuntimeError("当前车道无法构造有效测试路线")
    return route


def route_contains_junction(route: Sequence[RoutePoint]) -> bool:
    """判断采样路线是否经过 CARLA 标注的 junction。"""
    return any(point.is_junction for point in route)


class RouteTracker:
    """用最近路线点估计单调递增的路线完成率。"""

    def __init__(self, route: Sequence[RoutePoint], search_ahead: int = 5) -> None:
        if len(route) < 2:
            raise ValueError("route 至少需要两个点")
        self.route = list(route)
        self.search_ahead = search_ahead
        self.max_index = 0

    @property
    def route_length_m(self) -> float:
        return self.route[-1].distance_m

    def update(
        self,
        location: Any,
        max_progress_m: float | None = None,
    ) -> dict[str, float]:
        """更新车辆位置并返回路线进度、完成率与终点距离。"""
        end = min(len(self.route), self.max_index + self.search_ahead + 1)
        candidate_list = list(range(self.max_index, end))
        if max_progress_m is not None:
            bounded = [
                index
                for index in candidate_list
                if self.route[index].distance_m <= max_progress_m
            ]
            if bounded:
                candidate_list = bounded
        nearest = min(
            candidate_list,
            key=lambda index: math.hypot(
                float(location.x) - self.route[index].x,
                float(location.y) - self.route[index].y,
            ),
        )
        self.max_index = max(self.max_index, nearest)
        progress = self.route[self.max_index].distance_m
        goal = self.route[-1]
        goal_distance = math.sqrt(
            (float(location.x) - goal.x) ** 2
            + (float(location.y) - goal.y) ** 2
            + (float(location.z) - goal.z) ** 2
        )
        return {
            "route_progress_m": progress,
            "route_completion": min(progress / max(self.route_length_m, 1e-6), 1.0),
            "distance_to_goal_m": goal_distance,
        }
