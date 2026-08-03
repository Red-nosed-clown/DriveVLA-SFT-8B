#!/usr/bin/env python3
"""把 DriveVLA 六点轨迹转换为 CARLA 可执行控制量。

这个模块故意不导入 ``carla``，因此在模拟器尚未安装时也能运行单元测试。
CARLA agent 只需要把 :class:`ControlCommand` 转换为 ``carla.VehicleControl``。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence


Trajectory = Sequence[Sequence[float]]


@dataclass(frozen=True)
class ControllerConfig:
    """闭环控制和安全边界配置。

    nuScenes 关键帧间隔约 0.5 秒，因此六点轨迹默认覆盖未来 3 秒。项目坐标系
    中 lateral 正方向是左侧，而 CARLA ``steer`` 正方向是右侧，所以默认使用
    ``carla_steer_sign=-1`` 做显式坐标转换。
    """

    trajectory_points: int = 6
    trajectory_dt_s: float = 0.5
    wheelbase_m: float = 2.875
    max_steer_angle_deg: float = 35.0
    carla_steer_sign: float = -1.0
    min_lookahead_m: float = 3.0
    lookahead_time_s: float = 0.8
    max_target_speed_mps: float = 12.0
    slow_down_speed_mps: float = 4.0
    max_lateral_m: float = 12.0
    max_segment_m: float = 15.0
    backward_tolerance_m: float = 0.5
    prediction_timeout_s: float = 3.0
    speed_kp: float = 0.45
    speed_ki: float = 0.04
    speed_kd: float = 0.08
    integral_limit: float = 10.0
    brake_deadband: float = 0.10
    stop_speed_threshold_mps: float = 0.25


@dataclass(frozen=True)
class SafetyResult:
    """轨迹安全校验结果。"""

    valid: bool
    reason: str


@dataclass(frozen=True)
class ControlCommand:
    """与 ``carla.VehicleControl`` 字段对应的归一化控制命令。"""

    steer: float
    throttle: float
    brake: float
    target_speed_mps: float
    fallback: bool = False
    reason: str = "ok"


def _is_finite_point(point: Sequence[float]) -> bool:
    """检查一个轨迹点是否恰好包含两个有限数值。"""
    return (
        len(point) == 2
        and all(isinstance(value, (int, float)) for value in point)
        and all(math.isfinite(float(value)) for value in point)
    )


def validate_trajectory(
    trajectory: Trajectory,
    prediction_age_s: float,
    config: ControllerConfig,
) -> SafetyResult:
    """在控制器使用轨迹前执行确定性安全检查。"""
    if prediction_age_s < 0.0 or prediction_age_s > config.prediction_timeout_s:
        return SafetyResult(False, "prediction_timeout")
    if len(trajectory) != config.trajectory_points:
        return SafetyResult(False, "wrong_point_count")
    if not all(_is_finite_point(point) for point in trajectory):
        return SafetyResult(False, "non_finite_point")

    previous_forward = 0.0
    previous_lateral = 0.0
    for point in trajectory:
        forward, lateral = float(point[0]), float(point[1])
        if forward < previous_forward - config.backward_tolerance_m:
            return SafetyResult(False, "trajectory_moves_backward")
        if abs(lateral) > config.max_lateral_m:
            return SafetyResult(False, "lateral_out_of_bounds")
        if math.hypot(
            forward - previous_forward,
            lateral - previous_lateral,
        ) > config.max_segment_m:
            return SafetyResult(False, "segment_jump")
        previous_forward = forward
        previous_lateral = lateral

    if float(trajectory[-1][0]) < -config.backward_tolerance_m:
        return SafetyResult(False, "invalid_endpoint")
    return SafetyResult(True, "ok")


class WaypointController:
    """Pure Pursuit 横向控制与 PID 纵向控制的组合控制器。"""

    def __init__(self, config: ControllerConfig | None = None) -> None:
        self.config = config or ControllerConfig()
        self._integral_error = 0.0
        self._previous_speed_error = 0.0

    def reset(self) -> None:
        """场景切换或安全接管后清空 PID 状态。"""
        self._integral_error = 0.0
        self._previous_speed_error = 0.0

    def emergency_stop(self, reason: str) -> ControlCommand:
        """返回可预测的安全停车命令，并清空控制器历史状态。"""
        self.reset()
        return ControlCommand(
            steer=0.0,
            throttle=0.0,
            brake=1.0,
            target_speed_mps=0.0,
            fallback=True,
            reason=reason,
        )

    def run_step(
        self,
        trajectory: Trajectory,
        current_speed_mps: float,
        action: str = "KEEP_LANE",
        prediction_age_s: float = 0.0,
        control_dt_s: float = 0.05,
    ) -> ControlCommand:
        """根据最新轨迹和车速生成一步控制命令。"""
        safety = validate_trajectory(trajectory, prediction_age_s, self.config)
        if not safety.valid:
            return self.emergency_stop(safety.reason)
        if not math.isfinite(current_speed_mps) or current_speed_mps < 0.0:
            return self.emergency_stop("invalid_vehicle_speed")

        target_speed = self._estimate_target_speed(trajectory, action)
        steer = self._compute_steer(trajectory, current_speed_mps)
        throttle, brake = self._compute_longitudinal(
            current_speed_mps,
            target_speed,
            control_dt_s,
        )
        return ControlCommand(
            steer=steer,
            throttle=throttle,
            brake=brake,
            target_speed_mps=target_speed,
        )

    def _estimate_target_speed(self, trajectory: Trajectory, action: str) -> float:
        """按轨迹累计路程和预测时域估计期望速度。"""
        path_length = 0.0
        previous = (0.0, 0.0)
        for point in trajectory:
            current = (float(point[0]), float(point[1]))
            path_length += math.hypot(
                current[0] - previous[0],
                current[1] - previous[1],
            )
            previous = current

        horizon_s = len(trajectory) * self.config.trajectory_dt_s
        target_speed = path_length / max(horizon_s, 1e-3)
        target_speed = min(target_speed, self.config.max_target_speed_mps)
        if action == "STOP":
            return 0.0
        if action == "SLOW_DOWN":
            return min(target_speed, self.config.slow_down_speed_mps)
        return target_speed

    def _select_lookahead_point(
        self,
        trajectory: Trajectory,
        current_speed_mps: float,
    ) -> tuple[float, float]:
        """选择首个达到动态前视距离的轨迹点。"""
        lookahead = max(
            self.config.min_lookahead_m,
            current_speed_mps * self.config.lookahead_time_s,
        )
        for point in trajectory:
            forward, lateral = float(point[0]), float(point[1])
            if math.hypot(forward, lateral) >= lookahead:
                return forward, lateral
        endpoint = trajectory[-1]
        return float(endpoint[0]), float(endpoint[1])

    def _compute_steer(
        self,
        trajectory: Trajectory,
        current_speed_mps: float,
    ) -> float:
        """使用 Pure Pursuit 几何关系计算归一化转向量。"""
        forward, lateral = self._select_lookahead_point(
            trajectory,
            current_speed_mps,
        )
        distance_squared = max(forward * forward + lateral * lateral, 1e-6)
        curvature = 2.0 * lateral / distance_squared
        steering_angle = math.atan(self.config.wheelbase_m * curvature)
        normalized = steering_angle / math.radians(self.config.max_steer_angle_deg)
        carla_steer = self.config.carla_steer_sign * normalized
        return max(-1.0, min(1.0, carla_steer))

    def _compute_longitudinal(
        self,
        current_speed_mps: float,
        target_speed_mps: float,
        control_dt_s: float,
    ) -> tuple[float, float]:
        """使用带积分限幅的 PID 计算油门和制动。"""
        if target_speed_mps <= 0.0:
            self._integral_error = 0.0
            self._previous_speed_error = -current_speed_mps
            brake = 1.0 if current_speed_mps > self.config.stop_speed_threshold_mps else 0.3
            return 0.0, brake

        dt = max(control_dt_s, 1e-3)
        speed_error = target_speed_mps - current_speed_mps
        self._integral_error = max(
            -self.config.integral_limit,
            min(
                self.config.integral_limit,
                self._integral_error + speed_error * dt,
            ),
        )
        derivative = (speed_error - self._previous_speed_error) / dt
        self._previous_speed_error = speed_error
        effort = (
            self.config.speed_kp * speed_error
            + self.config.speed_ki * self._integral_error
            + self.config.speed_kd * derivative
        )

        if effort >= 0.0:
            return min(effort, 1.0), 0.0
        brake = min(-effort, 1.0)
        if brake < self.config.brake_deadband:
            brake = 0.0
        return 0.0, brake
