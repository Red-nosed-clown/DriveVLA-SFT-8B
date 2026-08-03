#!/usr/bin/env python3
"""构造与 v5 SFT 训练格式一致的 CARLA 在线 prompt。"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Sequence


@dataclass(frozen=True)
class NearbyActor:
    """CARLA 中相对 ego 的交通参与者。"""

    category: str
    distance_m: float
    forward_m: float
    lateral_m: float


@dataclass(frozen=True)
class SceneStats:
    """与 nuScenes v5 prompt 对齐的场景计数。"""

    vehicles: int
    pedestrians: int
    obstacles: int


@dataclass(frozen=True)
class EgoMotion:
    """最近 1.5 秒的 ego 运动摘要。"""

    history_steps: int
    history_duration_s: float
    history_speed_mps: Sequence[float]
    current_speed_mps: float
    history_accel_mps2: float
    history_yaw_delta_deg: float
    history_forward_delta_m: float
    history_lateral_delta_m: float


def build_online_prompt(
    scene_stats: SceneStats,
    nearby_actors: Sequence[NearbyActor],
    ego_motion: EgoMotion,
    navigation_instruction: str = "安全沿道路行驶。",
) -> str:
    """生成与 v5 数据字段和中文措辞一致的在线推理 prompt。"""
    closest = sorted(nearby_actors, key=lambda actor: actor.distance_m)[:8]
    closest_json = [
        {
            "category": actor.category,
            "distance_m": round(actor.distance_m, 2),
            "forward_m": round(actor.forward_m, 2),
            "lateral_m": round(actor.lateral_m, 2),
        }
        for actor in closest
    ]
    motion = asdict(ego_motion)
    motion["history_speed_mps"] = [
        round(float(speed), 2) for speed in ego_motion.history_speed_mps
    ]
    for key, value in list(motion.items()):
        if isinstance(value, float):
            motion[key] = round(value, 2)

    return (
        "你是自动驾驶视觉语言动作模型。根据前视相机图像和场景统计，预测自车未来"
        "驾驶动作、启发式风险等级和未来轨迹。只输出合法 JSON，不要输出 Markdown。"
        "字段必须为 action、risk、trajectory、reason；trajectory 必须包含未来 6 个 "
        "[forward_m, lateral_m] 点。\n"
        f"驾驶指令：{navigation_instruction}\n"
        "场景统计："
        f"{json.dumps(asdict(scene_stats), ensure_ascii=False)}\n"
        "最近目标："
        f"{json.dumps(closest_json, ensure_ascii=False)}\n"
        "历史自车运动："
        f"{json.dumps(motion, ensure_ascii=False)}\n"
        "运动提示：历史速度用于判断 KEEP_LANE、SLOW_DOWN 和 STOP；未来轨迹点间距"
        "应反映速度变化，横向变化应反映道路转向趋势。"
    )
