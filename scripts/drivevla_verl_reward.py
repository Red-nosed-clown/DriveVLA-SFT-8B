#!/usr/bin/env python3
"""VERL 使用的 DriveVLA 可验证轨迹奖励函数。"""

from __future__ import annotations

import json
import math
from typing import Any

from scripts.parse_outputs import extract_first_json_object, parse_model_output


def as_ground_truth(value: Any) -> dict[str, Any]:
    """兼容 parquet 返回的 JSON 字符串或字典。"""
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, dict):
        raise TypeError("ground_truth 必须是 JSON 对象或 JSON 字符串")
    return value


def trajectory_errors(prediction: list[list[float]], target: list[list[float]]) -> tuple[float, float]:
    """计算六点轨迹 ADE 和 FDE。"""
    distances = [
        math.hypot(float(pred[0]) - float(gt[0]), float(pred[1]) - float(gt[1]))
        for pred, gt in zip(prediction, target, strict=True)
    ]
    return sum(distances) / len(distances), distances[-1]


def geometry_valid(trajectory: list[list[float]]) -> bool:
    """检查轨迹是否前向基本单调、相邻点无跳变且横向不越界。"""
    previous = [0.0, 0.0]
    for point in trajectory:
        if point[0] < previous[0] - 0.5:
            return False
        if abs(point[1]) > 12.0:
            return False
        if math.hypot(point[0] - previous[0], point[1] - previous[1]) > 15.0:
            return False
        previous = point
    return True


def direction_consistent(action: str, trajectory: list[list[float]]) -> bool:
    """动作方向必须与最终横向位移一致。"""
    final_lateral = trajectory[-1][1]
    if action == "TURN_LEFT":
        return final_lateral > 0.3
    if action == "TURN_RIGHT":
        return final_lateral < -0.3
    return True


def compute_score(
    data_source: str,
    solution_str: str,
    ground_truth: Any,
    extra_info: dict[str, Any] | None = None,
) -> dict[str, float]:
    """返回总奖励和分项指标，便于在 VERL 日志中发现奖励投机。"""
    del data_source
    extra_info = extra_info or {}
    target = as_ground_truth(ground_truth)
    parsed = parse_model_output(solution_str)
    exact_object = extract_first_json_object(solution_str)
    exact_json = exact_object is not None and exact_object.strip() == solution_str.strip()

    components = {
        "format": 0.15 if parsed["parse_success"] and exact_json else 0.0,
        "action": 0.10 if parsed["action"] == target["action"] else 0.0,
        "risk": 0.05 if parsed["risk"] == target["risk"] else 0.0,
        "trajectory": 0.0,
        "endpoint": 0.0,
        "speed": 0.0,
        "geometry": 0.0,
        "consistency": 0.0,
        "penalty": 0.0,
    }

    prediction = parsed.get("trajectory")
    if prediction is not None:
        ade, fde = trajectory_errors(prediction, target["trajectory"])
        components["trajectory"] = 0.25 * math.exp(-ade / 2.0)
        components["endpoint"] = 0.15 * math.exp(-fde / 3.0)
        valid_geometry = geometry_valid(prediction)
        components["geometry"] = 0.10 if valid_geometry else 0.0
        components["consistency"] = 0.10 if direction_consistent(parsed["action"], prediction) else 0.0
        if not valid_geometry:
            components["penalty"] -= 0.5
    else:
        ade, fde = 99.0, 99.0

    predicted_speed = parsed.get("target_speed_mps")
    target_speed = float(target.get("target_speed_mps", 0.0))
    if isinstance(predicted_speed, (int, float)):
        speed_error = abs(float(predicted_speed) - target_speed)
        components["speed"] = 0.10 * math.exp(-speed_error / 2.0)
    else:
        speed_error = 99.0

    no_hazard = not bool(extra_info.get("visible_forward_hazard", False))
    if no_hazard and target["action"] != "STOP" and parsed["action"] == "STOP":
        components["penalty"] -= 0.5
    if (
        no_hazard
        and target["action"] != "STOP"
        and parsed["action"] == "SLOW_DOWN"
        and isinstance(predicted_speed, (int, float))
        and float(predicted_speed) < 1.5
    ):
        components["penalty"] -= 0.3
    if prediction is not None and not direction_consistent(parsed["action"], prediction):
        components["penalty"] -= 0.3

    score = max(-1.0, min(1.0, sum(components.values())))
    return {
        "score": score,
        **{f"reward_{name}": value for name, value in components.items()},
        "ade": ade,
        "fde": fde,
        "speed_error": speed_error,
        "parse_success": float(parsed["parse_success"]),
    }
