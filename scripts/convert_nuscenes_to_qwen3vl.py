#!/usr/bin/env python3
"""把本地 nuScenes-mini 转换为 Qwen3-VL VLA 指令微调数据。"""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


CAMERA_CHANNELS = (
    "CAM_FRONT",
    "CAM_FRONT_LEFT",
    "CAM_FRONT_RIGHT",
    "CAM_BACK",
    "CAM_BACK_LEFT",
    "CAM_BACK_RIGHT",
)
VALID_ACTIONS = ("KEEP_LANE", "TURN_LEFT", "TURN_RIGHT", "SLOW_DOWN", "STOP")
VALID_RISKS = ("LOW", "MEDIUM", "HIGH")


def load_json(path: Path) -> list[dict[str, Any]]:
    """读取 nuScenes JSON 表，并在文件缺失时给出明确错误。"""
    if not path.exists():
        raise FileNotFoundError(f"缺少 nuScenes 元数据文件：{path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"期望 {path} 的顶层结构为列表")
    return data


def dump_json(path: Path, data: Any) -> None:
    """以 UTF-8 写入格式化 JSON。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def dump_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    """逐行写入 JSONL，供自写推理与评估脚本使用。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def yaw_from_quaternion(rotation: list[float]) -> float:
    """从 nuScenes 的 w、x、y、z 四元数中计算平面 yaw。"""
    w, x, y, z = rotation
    return math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


def world_to_ego_xy(
    current_pose: dict[str, Any],
    future_pose: dict[str, Any],
) -> list[float]:
    """将未来世界坐标转换到当前自车坐标系，返回前向和横向位移。"""
    dx = future_pose["translation"][0] - current_pose["translation"][0]
    dy = future_pose["translation"][1] - current_pose["translation"][1]
    yaw = yaw_from_quaternion(current_pose["rotation"])
    forward = math.cos(yaw) * dx + math.sin(yaw) * dy
    lateral = -math.sin(yaw) * dx + math.cos(yaw) * dy
    return [round(forward, 2), round(lateral, 2)]


def build_channel_lookup(
    sample_data: list[dict[str, Any]],
    calibrated_sensor: list[dict[str, Any]],
    sensors: list[dict[str, Any]],
) -> dict[str, dict[str, dict[str, Any]]]:
    """建立 sample_token 到各相机关键帧 sample_data 的索引。"""
    sensor_by_token = {item["token"]: item for item in sensors}
    channel_by_calibrated = {
        item["token"]: sensor_by_token[item["sensor_token"]]["channel"]
        for item in calibrated_sensor
    }
    lookup: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for item in sample_data:
        channel = channel_by_calibrated[item["calibrated_sensor_token"]]
        if channel in CAMERA_CHANNELS and item.get("is_key_frame", False):
            lookup[item["sample_token"]][channel] = item
    return lookup


def collect_future_samples(
    sample: dict[str, Any],
    sample_by_token: dict[str, dict[str, Any]],
    future_steps: int,
) -> list[dict[str, Any]] | None:
    """沿 sample.next 收集未来关键帧；不足指定步数时返回 None。"""
    future_samples: list[dict[str, Any]] = []
    current = sample
    for _ in range(future_steps):
        next_token = current.get("next", "")
        if not next_token:
            return None
        current = sample_by_token[next_token]
        future_samples.append(current)
    return future_samples


def collect_previous_samples(
    sample: dict[str, Any],
    sample_by_token: dict[str, dict[str, Any]],
    history_steps: int,
) -> list[dict[str, Any]] | None:
    """沿 sample.prev 收集历史关键帧，并按时间从旧到新返回。

    v5 需要让模型看到“过去一小段时间自车怎么运动”。如果 scene 开头历史不足，
    直接跳过该样本，避免有的样本带历史、有的样本不带历史导致 prompt 分布混乱。
    """
    if history_steps <= 0:
        return []

    previous_samples: list[dict[str, Any]] = []
    current = sample
    for _ in range(history_steps):
        previous_token = current.get("prev", "")
        if not previous_token:
            return None
        current = sample_by_token[previous_token]
        previous_samples.append(current)
    previous_samples.reverse()
    return previous_samples


def build_future_trajectory(
    current_pose: dict[str, Any],
    future_poses: list[dict[str, Any]],
) -> list[list[float]]:
    """生成当前自车坐标系下的多点未来轨迹。"""
    return [world_to_ego_xy(current_pose, pose) for pose in future_poses]


def trajectory_path_length(trajectory: list[list[float]]) -> float:
    """计算一条未来轨迹从自车原点出发的累计路程。

    输入：
        trajectory：当前自车坐标系下的六个 ``[forward, lateral]`` 点。

    输出：
        相邻轨迹点欧氏距离之和，单位为米。

    为什么这样做：
        最后一个点到原点的直线距离不能表示弯道中的实际运动路程。把原点和
        六个点依次相连后累加，更适合作为数据报告中的平均轨迹长度。
    """
    points = [[0.0, 0.0], *trajectory]
    return sum(
        math.hypot(current[0] - previous[0], current[1] - previous[1])
        for previous, current in zip(points, points[1:])
    )


def trajectory_step_distances(trajectory: list[list[float]]) -> list[float]:
    """计算从自车原点到未来六点之间每一小段的距离。

    这些距离只写入 metadata 和数据报告，不放进 prompt。原因是它们来自未来轨迹，
    如果直接提供给模型，就等于把答案的一部分泄漏给输入端。
    """
    points = [[0.0, 0.0], *trajectory]
    return [
        math.hypot(current[0] - previous[0], current[1] - previous[1])
        for previous, current in zip(points, points[1:])
    ]


def trajectory_motion_stats(trajectory: list[list[float]]) -> dict[str, float]:
    """提取动作弱标签需要的未来运动统计量。

    初学者提示：
        action 标签不是人工标注，而是根据 ego pose 轨迹推出来的弱监督标签。
        把这些中间量保存下来，后面检查标签是否合理时就不用只看最终类别。
    """
    final_forward, final_lateral = trajectory[-1]
    step_distances = trajectory_step_distances(trajectory)
    path_length = sum(step_distances)
    first_step = step_distances[0] if step_distances else 0.0
    last_step = step_distances[-1] if step_distances else 0.0
    max_abs_lateral = max(abs(point[1]) for point in trajectory) if trajectory else 0.0
    return {
        "final_forward_m": round(final_forward, 2),
        "final_lateral_m": round(final_lateral, 2),
        "path_length_m": round(path_length, 2),
        "avg_step_m": round(path_length / len(step_distances), 2) if step_distances else 0.0,
        "first_step_m": round(first_step, 2),
        "last_step_m": round(last_step, 2),
        "step_delta_m": round(last_step - first_step, 2),
        "max_abs_lateral_m": round(max_abs_lateral, 2),
    }


def infer_target_speed_mps(trajectory: list[list[float]], step_duration_s: float = 0.5) -> float:
    """用未来最后一段轨迹估计监督用目标速度。

    该数值属于模型需要预测的标签，只能写入 assistant 输出，不能放进用户 prompt。
    nuScenes 关键帧通常间隔约 0.5 秒，因此默认使用 0.5 秒换算。
    """
    if step_duration_s <= 0.0:
        raise ValueError("step_duration_s 必须大于 0")
    distances = trajectory_step_distances(trajectory)
    return round(distances[-1] / step_duration_s, 2) if distances else 0.0


def normalize_angle(angle_rad: float) -> float:
    """把角度归一化到 [-pi, pi]，避免跨越 180 度时差值跳变。"""
    return math.atan2(math.sin(angle_rad), math.cos(angle_rad))


def build_history_motion(
    current_pose: dict[str, Any],
    history_poses: list[dict[str, Any]],
    current_timestamp: int,
    history_timestamps: list[int],
) -> dict[str, Any]:
    """根据历史 ego pose 生成可放进 prompt 的自车运动状态。

    这些量只来自当前帧之前的 ego pose，不使用未来轨迹，因此不会把答案泄漏给输入端。
    初学者可以把它理解为给模型补上“速度表”和“过去 1.5 秒方向盘趋势”的简化版本。
    """
    all_poses = [*history_poses, current_pose]
    all_timestamps = [*history_timestamps, current_timestamp]

    speeds: list[float] = []
    for previous_pose, current_pose_item, previous_time, current_time in zip(
        all_poses,
        all_poses[1:],
        all_timestamps,
        all_timestamps[1:],
    ):
        dt = max((current_time - previous_time) / 1_000_000.0, 1e-6)
        dx = current_pose_item["translation"][0] - previous_pose["translation"][0]
        dy = current_pose_item["translation"][1] - previous_pose["translation"][1]
        speeds.append(round(math.hypot(dx, dy) / dt, 2))

    current_speed = speeds[-1] if speeds else 0.0
    if len(speeds) >= 2:
        elapsed = max((all_timestamps[-1] - all_timestamps[1]) / 1_000_000.0, 1e-6)
        accel = (speeds[-1] - speeds[0]) / elapsed
    else:
        accel = 0.0

    oldest_pose = history_poses[0] if history_poses else current_pose
    oldest_position_in_current_ego = world_to_ego_xy(current_pose, oldest_pose)
    history_forward_delta = -oldest_position_in_current_ego[0]
    history_lateral_delta = -oldest_position_in_current_ego[1]
    yaw_delta = normalize_angle(
        yaw_from_quaternion(current_pose["rotation"])
        - yaw_from_quaternion(oldest_pose["rotation"])
    )

    return {
        "history_steps": len(history_poses),
        "history_duration_s": round((current_timestamp - all_timestamps[0]) / 1_000_000.0, 2),
        "history_speed_mps": speeds,
        "current_speed_mps": round(current_speed, 2),
        "history_accel_mps2": round(accel, 2),
        "history_yaw_delta_deg": round(math.degrees(yaw_delta), 2),
        "history_forward_delta_m": round(history_forward_delta, 2),
        "history_lateral_delta_m": round(history_lateral_delta, 2),
    }


def infer_action_token_legacy(trajectory: list[list[float]]) -> str:
    """根据最终轨迹点生成 v1 简化驾驶动作标签。"""
    final_forward, final_lateral = trajectory[-1]
    if final_forward < 1.0:
        return "STOP"
    if final_lateral > 1.0:
        return "TURN_LEFT"
    if final_lateral < -1.0:
        return "TURN_RIGHT"
    if final_forward < 3.0:
        return "SLOW_DOWN"
    return "KEEP_LANE"


def infer_action_token_v2(trajectory: list[list[float]]) -> str:
    """使用更细的运动统计生成 v2 动作标签。

    v1 的 SLOW_DOWN 只看未来终点是否小于 3 米，容易漏掉“还在前进但明显很慢”
    的样本。v2 同时看累计路程、平均每段位移和最后一段位移，让低速类样本更容易
    被标出来。阈值仍是 heuristic 弱监督规则，后续需要用数据报告和失败样本继续调。
    """
    stats = trajectory_motion_stats(trajectory)
    final_forward = stats["final_forward_m"]
    final_lateral = stats["final_lateral_m"]
    path_length = stats["path_length_m"]
    avg_step = stats["avg_step_m"]
    last_step = stats["last_step_m"]
    step_delta = stats["step_delta_m"]

    if path_length < 1.2 or final_forward < 1.0:
        return "STOP"
    if final_lateral > 1.2:
        return "TURN_LEFT"
    if final_lateral < -1.2:
        return "TURN_RIGHT"
    if final_forward < 6.0 or avg_step < 1.0 or last_step < 0.8 or step_delta < -0.8:
        return "SLOW_DOWN"
    return "KEEP_LANE"


def infer_action_token_v3(
    trajectory: list[list[float]],
    history_motion: dict[str, Any] | None = None,
) -> str:
    """结合未来轨迹和历史速度趋势生成更干净的 v3 动作弱标签。

    v2 的问题是只要未来前向距离偏短，就容易把 KEEP_LANE 标成 SLOW_DOWN。
    v3 仍然只用规则生成弱标签，但会更强调“速度真的在下降”：
        1. 明显横向位移先归为转向，避免弯道样本被误标为减速；
        2. SLOW_DOWN 需要未来步长下降、未来速度偏低，或历史当前速度到未来末段
           存在明显下降；
        3. STOP 仍优先处理近乎静止的样本。
    """
    stats = trajectory_motion_stats(trajectory)
    final_forward = stats["final_forward_m"]
    final_lateral = stats["final_lateral_m"]
    path_length = stats["path_length_m"]
    avg_step = stats["avg_step_m"]
    first_step = stats["first_step_m"]
    last_step = stats["last_step_m"]
    step_delta = stats["step_delta_m"]

    if path_length < 1.2 or final_forward < 1.0:
        return "STOP"
    if final_lateral > 1.2:
        return "TURN_LEFT"
    if final_lateral < -1.2:
        return "TURN_RIGHT"

    future_avg_speed = avg_step / 0.5
    future_last_speed = last_step / 0.5
    future_decelerating = first_step >= 1.5 and step_delta <= -0.9
    future_low_speed = final_forward < 6.0 and future_avg_speed < 2.8
    history_to_future_drop = False
    if history_motion:
        current_speed = float(history_motion.get("current_speed_mps", 0.0))
        history_to_future_drop = current_speed >= 3.0 and future_last_speed <= current_speed - 1.2

    if future_low_speed or future_decelerating or history_to_future_drop:
        return "SLOW_DOWN"
    return "KEEP_LANE"


def infer_action_token(
    trajectory: list[list[float]],
    action_rule: str = "legacy",
    history_motion: dict[str, Any] | None = None,
) -> str:
    """按指定规则推断动作标签，默认保持 v1 行为不变。"""
    if action_rule == "legacy":
        return infer_action_token_legacy(trajectory)
    if action_rule == "v2":
        return infer_action_token_v2(trajectory)
    if action_rule == "v3":
        return infer_action_token_v3(trajectory, history_motion)
    raise ValueError(f"未知动作规则：{action_rule}")


def classify_category(category_name: str) -> str:
    """把 nuScenes 细分类别汇总为车辆、行人和障碍物。"""
    if category_name.startswith("vehicle."):
        return "vehicle"
    if category_name.startswith("human.pedestrian"):
        return "pedestrian"
    return "obstacle"


def summarize_objects(
    sample_token: str,
    annotations_by_sample: dict[str, list[dict[str, Any]]],
    instance_by_token: dict[str, dict[str, Any]],
    category_by_token: dict[str, dict[str, Any]],
    current_pose: dict[str, Any],
    max_objects: int,
    annotation_by_token: dict[str, dict[str, Any]] | None = None,
    sample_by_token: dict[str, dict[str, Any]] | None = None,
    ego_speed_mps: float = 0.0,
    include_object_motion: bool = False,
) -> dict[str, Any]:
    """统计交通参与者，并提取距离和历史运动信息。

    v6 只通过 annotation.prev 读取目标过去的位置，绝不读取 annotation.next，
    因此目标速度和 TTC 不会泄漏未来答案。
    """
    counts = {"vehicles": 0, "pedestrians": 0, "obstacles": 0}
    nearest: list[dict[str, Any]] = []
    yaw = yaw_from_quaternion(current_pose["rotation"])
    for annotation in annotations_by_sample.get(sample_token, []):
        instance = instance_by_token.get(annotation["instance_token"], {})
        category = category_by_token.get(instance.get("category_token", ""), {})
        category_name = category.get("name", "unknown")
        group = classify_category(category_name)
        counts[f"{group}s"] += 1

        dx = annotation["translation"][0] - current_pose["translation"][0]
        dy = annotation["translation"][1] - current_pose["translation"][1]
        forward = math.cos(yaw) * dx + math.sin(yaw) * dy
        lateral = -math.sin(yaw) * dx + math.cos(yaw) * dy
        actor_info: dict[str, Any] = {
            "category": category_name,
            "distance_m": round(math.hypot(forward, lateral), 2),
            "forward_m": round(forward, 2),
            "lateral_m": round(lateral, 2),
        }
        if include_object_motion:
            longitudinal_speed = None
            previous = (annotation_by_token or {}).get(annotation.get("prev", ""))
            current_sample = (sample_by_token or {}).get(annotation["sample_token"])
            previous_sample = (
                (sample_by_token or {}).get(previous["sample_token"])
                if previous is not None
                else None
            )
            if current_sample is not None and previous_sample is not None:
                dt = (current_sample["timestamp"] - previous_sample["timestamp"]) / 1_000_000.0
                if dt > 0.0:
                    vx = (annotation["translation"][0] - previous["translation"][0]) / dt
                    vy = (annotation["translation"][1] - previous["translation"][1]) / dt
                    longitudinal_speed = math.cos(yaw) * vx + math.sin(yaw) * vy

            relative_longitudinal = (
                longitudinal_speed - ego_speed_mps
                if longitudinal_speed is not None
                else None
            )
            closing_speed = (
                max(0.0, -relative_longitudinal)
                if relative_longitudinal is not None
                else None
            )
            ttc = (
                forward / closing_speed
                if closing_speed is not None
                and closing_speed >= 0.5
                and forward > 0.0
                and abs(lateral) <= 4.0
                else None
            )
            actor_info.update(
                {
                    "longitudinal_speed_mps": (
                        round(longitudinal_speed, 2) if longitudinal_speed is not None else None
                    ),
                    "relative_longitudinal_speed_mps": (
                        round(relative_longitudinal, 2)
                        if relative_longitudinal is not None
                        else None
                    ),
                    "closing_speed_mps": round(closing_speed, 2) if closing_speed is not None else None,
                    "ttc_s": round(min(ttc, 99.0), 2) if ttc is not None else None,
                }
            )
        nearest.append(actor_info)
    nearest.sort(key=lambda item: item["distance_m"])
    return {"counts": counts, "nearest": nearest[:max_objects]}


def infer_risk_level(counts: dict[str, int]) -> tuple[str, float]:
    """使用透明的弱规则生成风险标签，便于复现和说明局限性。"""
    score = (
        counts["vehicles"] * 0.05
        + counts["pedestrians"] * 0.08
        + counts["obstacles"] * 0.04
    )
    if score >= 2.2:
        return "HIGH", round(score, 2)
    if score >= 1.0:
        return "MEDIUM", round(score, 2)
    return "LOW", round(score, 2)


def build_reason(action: str, risk: str) -> str:
    """生成稳定的短解释，避免把未来轨迹数值直接泄漏到 reason。"""
    action_text = {
        "KEEP_LANE": "保持当前车道并平稳前进",
        "TURN_LEFT": "沿道路趋势向左行驶",
        "TURN_RIGHT": "沿道路趋势向右行驶",
        "SLOW_DOWN": "降低速度并继续观察前方",
        "STOP": "停车或低速等待",
    }[action]
    risk_text = {
        "LOW": "周边交通参与者较少",
        "MEDIUM": "周边存在一定数量的交通参与者",
        "HIGH": "周边交通参与者密集，需要谨慎决策",
    }[risk]
    return f"{action_text}；{risk_text}。"


def make_record(
    sample: dict[str, Any],
    image_path: Path,
    trajectory: list[list[float]],
    object_summary: dict[str, Any],
    future_steps: int,
    action_rule: str,
    history_motion: dict[str, Any] | None = None,
    include_speed_target: bool = False,
) -> dict[str, Any]:
    """构造自写脚本可读的 Qwen3-VL 多模态 SFT 样本。"""
    action = infer_action_token(trajectory, action_rule, history_motion)
    risk, risk_score = infer_risk_level(object_summary["counts"])
    answer = {
        "action": action,
        "risk": risk,
        "trajectory": trajectory,
        "reason": build_reason(action, risk),
    }
    if include_speed_target:
        answer["target_speed_mps"] = infer_target_speed_mps(trajectory)
    history_text = ""
    if history_motion:
        history_text = (
            f"\n历史自车运动：{json.dumps(history_motion, ensure_ascii=False)}"
            "\n运动提示：历史速度用于判断 KEEP_LANE、SLOW_DOWN 和 STOP；"
            "未来轨迹点间距应反映速度变化，横向变化应反映道路转向趋势。"
        )
    required_fields = "action、risk、trajectory、reason"
    if include_speed_target:
        required_fields += "、target_speed_mps"
    prompt = (
        "你是自动驾驶视觉语言动作模型。根据前视相机图像和场景统计，"
        "预测自车未来驾驶动作、启发式风险等级和未来轨迹。"
        "只输出合法 JSON，不要输出 Markdown。"
        f"字段必须为 {required_fields}；"
        f"trajectory 必须包含未来 {future_steps} 个 [forward_m, lateral_m] 点。\n"
        "驾驶指令：安全沿道路行驶。\n"
        f"场景统计：{json.dumps(object_summary['counts'], ensure_ascii=False)}\n"
        f"最近目标：{json.dumps(object_summary['nearest'], ensure_ascii=False)}"
        f"{history_text}"
    )
    return {
        "id": sample["token"],
        "image": str(image_path),
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": str(image_path)},
                    {"type": "text", "text": prompt},
                ],
            },
            {
                "role": "assistant",
                "content": [{"type": "text", "text": json.dumps(answer, ensure_ascii=False)}],
            },
        ],
        "ground_truth": answer,
        "metadata": {
            "sample_token": sample["token"],
            "scene_token": sample["scene_token"],
            "image": str(image_path),
            "action": action,
            "risk": risk,
            "risk_score": risk_score,
            "object_counts": object_summary["counts"],
            "nearest_objects": object_summary["nearest"],
            "history_motion": history_motion or {},
            "motion_stats": trajectory_motion_stats(trajectory),
            "action_rule": action_rule,
        },
    }


def to_llamafactory_row(row: dict[str, Any]) -> dict[str, Any]:
    """转换为 LLaMA-Factory 支持的 ShareGPT 多模态格式。"""
    user_content = row["messages"][0]["content"]
    prompt = next(item["text"] for item in user_content if item["type"] == "text")
    answer = row["messages"][1]["content"][0]["text"]
    return {
        "messages": [
            {"role": "user", "content": f"<image>{prompt}"},
            {"role": "assistant", "content": answer},
        ],
        "images": [row["image"]],
    }


def split_by_scene(
    rows: list[dict[str, Any]],
    val_ratio: float,
    seed: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], set[str], set[str]]:
    """按 scene 切分数据，避免同一路段相邻帧同时进入训练和验证集。"""
    scene_tokens = sorted({row["metadata"]["scene_token"] for row in rows})
    random.Random(seed).shuffle(scene_tokens)
    val_scene_count = max(1, round(len(scene_tokens) * val_ratio))
    val_scenes = set(scene_tokens[:val_scene_count])
    train_scenes = set(scene_tokens[val_scene_count:])
    train_rows = [row for row in rows if row["metadata"]["scene_token"] in train_scenes]
    val_rows = [row for row in rows if row["metadata"]["scene_token"] in val_scenes]
    return train_rows, val_rows, train_scenes, val_scenes


def balance_training_rows(
    train_rows: list[dict[str, Any]],
    seed: int,
    target_count: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """对训练集做动作均衡采样，验证集不要调用这个函数。

    做法：
        1. 先按 action 分组；
        2. 少于目标数量的类别用有放回采样补齐；
        3. 多于目标数量的类别随机下采样；
        4. 最后整体打乱。

    为什么只处理训练集：
        验证集要保留真实分布，否则评估指标会变得好看但不可信。
    """
    rng = random.Random(seed)
    groups: dict[str, list[dict[str, Any]]] = {action: [] for action in VALID_ACTIONS}
    for row in train_rows:
        groups[row["metadata"]["action"]].append(row)

    original_distribution = {
        action: len(groups[action])
        for action in VALID_ACTIONS
        if groups[action]
    }
    if not original_distribution:
        return train_rows, {"enabled": False, "reason": "empty_train_rows"}

    if target_count <= 0:
        # 默认不要把所有类别补到 KEEP_LANE 的数量，否则训练集会膨胀过大。
        # 这里使用“非 KEEP_LANE 类别里的最大数量”作为目标，既提升少数类权重，
        # 又能顺手压低 KEEP_LANE 的占比，适合先做短训练对照实验。
        non_keep_counts = [
            count
            for action, count in original_distribution.items()
            if action != "KEEP_LANE"
        ]
        target_count = max(non_keep_counts) if non_keep_counts else max(original_distribution.values())

    balanced_rows: list[dict[str, Any]] = []
    for action in VALID_ACTIONS:
        rows = groups[action]
        if not rows:
            continue
        if len(rows) >= target_count:
            balanced_rows.extend(rng.sample(rows, target_count))
        else:
            balanced_rows.extend(rows)
            balanced_rows.extend(rng.choice(rows) for _ in range(target_count - len(rows)))

    rng.shuffle(balanced_rows)
    balanced_distribution = Counter(row["metadata"]["action"] for row in balanced_rows)
    return balanced_rows, {
        "enabled": True,
        "mode": "equal_per_action",
        "target_per_action": target_count,
        "original_distribution": original_distribution,
        "balanced_distribution": dict(balanced_distribution),
    }


def parse_action_target_counts(raw_targets: str) -> dict[str, int]:
    """解析每类 action 的目标采样数量。

    输入示例：
        ``'{"SLOW_DOWN": 7000, "TURN_LEFT": 3000}'``

    为什么使用 JSON：
        JSON 比逗号分隔字符串更不容易写错，也方便把真实实验配置原样记录到
        summary.json 和 README 里。
    """
    if not raw_targets:
        return {}
    parsed = json.loads(raw_targets)
    if not isinstance(parsed, dict):
        raise ValueError("--action-target-counts-json 必须是 JSON 对象")

    targets: dict[str, int] = {}
    for action, count in parsed.items():
        if action not in VALID_ACTIONS:
            raise ValueError(f"未知 action：{action}")
        if not isinstance(count, int) or count < 0:
            raise ValueError(f"{action} 的目标数量必须是非负整数")
        targets[action] = count
    return targets


def sample_training_rows_by_action_targets(
    train_rows: list[dict[str, Any]],
    seed: int,
    target_counts: dict[str, int],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """按每类 action 的目标数量采样训练集，验证集不要调用这个函数。

    和 ``balance_training_rows`` 的区别：
        ``balance_training_rows`` 会把所有类别采到同一个数量，适合测试强均衡；
        这个函数只调整用户指定的类别，未指定类别保持原始数量，适合 v4 这种
        温和采样消融实验。
    """
    rng = random.Random(seed)
    groups: dict[str, list[dict[str, Any]]] = {action: [] for action in VALID_ACTIONS}
    for row in train_rows:
        groups[row["metadata"]["action"]].append(row)

    original_distribution = {
        action: len(groups[action])
        for action in VALID_ACTIONS
        if groups[action]
    }
    if not original_distribution:
        return train_rows, {"enabled": False, "reason": "empty_train_rows"}

    final_targets = {
        action: target_counts.get(action, len(groups[action]))
        for action in VALID_ACTIONS
        if groups[action]
    }

    sampled_rows: list[dict[str, Any]] = []
    for action in VALID_ACTIONS:
        rows = groups[action]
        if not rows:
            continue
        target_count = final_targets[action]
        if target_count <= 0:
            continue
        if len(rows) >= target_count:
            sampled_rows.extend(rng.sample(rows, target_count))
        else:
            sampled_rows.extend(rows)
            sampled_rows.extend(rng.choice(rows) for _ in range(target_count - len(rows)))

    rng.shuffle(sampled_rows)
    sampled_distribution = Counter(row["metadata"]["action"] for row in sampled_rows)
    return sampled_rows, {
        "enabled": True,
        "mode": "custom_action_targets",
        "requested_targets": target_counts,
        "final_targets": final_targets,
        "original_distribution": original_distribution,
        "balanced_distribution": dict(sampled_distribution),
    }


def build_report(
    rows: list[dict[str, Any]],
    train_rows: list[dict[str, Any]],
    val_rows: list[dict[str, Any]],
    train_scenes: set[str],
    val_scenes: set[str],
    skipped: Counter[str],
    action_rule: str,
    balance_info: dict[str, Any],
    history_steps: int,
    include_object_motion: bool,
    include_speed_target: bool,
) -> str:
    """生成可直接放入项目文档的数据集统计报告。"""
    action_counts = Counter(row["metadata"]["action"] for row in rows)
    train_action_counts = Counter(row["metadata"]["action"] for row in train_rows)
    val_action_counts = Counter(row["metadata"]["action"] for row in val_rows)
    risk_counts = Counter(row["metadata"]["risk"] for row in rows)
    average_path_length = (
        mean(trajectory_path_length(row["ground_truth"]["trajectory"]) for row in rows)
        if rows
        else 0.0
    )
    nearest_objects = [
        actor
        for row in rows
        for actor in row["metadata"].get("nearest_objects", [])
    ]
    motion_objects = [
        actor for actor in nearest_objects if actor.get("longitudinal_speed_mps") is not None
    ]
    ttc_objects = [actor for actor in nearest_objects if actor.get("ttc_s") is not None]
    lines = [
        "# nuScenes VLA 数据报告",
        "",
        "## 数据概览",
        "",
        f"- 成功转换：{len(rows)}",
        f"- 训练样本：{len(train_rows)}",
        f"- 验证样本：{len(val_rows)}",
        f"- 训练场景：{len(train_scenes)}",
        f"- 验证场景：{len(val_scenes)}",
        f"- 轨迹点数：{len(rows[0]['ground_truth']['trajectory']) if rows else 0}",
        f"- 动作标签规则：{action_rule}",
        f"- 历史自车运动步数：{history_steps}",
        f"- 最近目标历史运动与 TTC：{include_object_motion}",
        f"- 目标速度监督：{include_speed_target}",
        f"- 最近目标历史速度覆盖率：{len(motion_objects) / max(len(nearest_objects), 1):.2%}",
        f"- 可计算 TTC 的目标数：{len(ttc_objects)}",
        f"- 训练集动作均衡采样：{balance_info.get('enabled', False)}",
        f"- 平均未来轨迹路程：{average_path_length:.2f} 米",
        f"- scene 开头历史帧不足：{skipped['insufficient_history']}",
        f"- 缺失图片：{skipped['missing_image']}",
        f"- scene 末尾未来帧不足：{skipped['insufficient_future']}",
        f"- 缺失相机关键帧：{skipped['missing_camera']}",
        "",
        "## Action 分布",
        "",
    ]
    lines.extend(f"- {name}: {action_counts.get(name, 0)}" for name in VALID_ACTIONS)
    lines.extend(["", "## 训练集 Action 分布", ""])
    lines.extend(f"- {name}: {train_action_counts.get(name, 0)}" for name in VALID_ACTIONS)
    lines.extend(["", "## 验证集 Action 分布", ""])
    lines.extend(f"- {name}: {val_action_counts.get(name, 0)}" for name in VALID_ACTIONS)
    lines.extend(["", "## Risk 分布", ""])
    lines.extend(f"- {name}: {risk_counts.get(name, 0)}" for name in VALID_RISKS)
    if balance_info.get("enabled"):
        lines.extend(
            [
                "",
                "## 训练集均衡采样说明",
                "",
                f"- 采样模式：{balance_info.get('mode', 'unknown')}",
                f"- 每类目标样本数：{balance_info.get('target_per_action', 'custom')}",
                f"- 自定义目标：{json.dumps(balance_info.get('final_targets', {}), ensure_ascii=False)}",
                f"- 均衡前：{json.dumps(balance_info['original_distribution'], ensure_ascii=False)}",
                f"- 均衡后：{json.dumps(balance_info['balanced_distribution'], ensure_ascii=False)}",
                "- 均衡采样只影响训练文件，验证文件保持 scene split 后的真实分布。",
            ]
        )
    lines.extend(
        [
            "",
            "## 标签说明",
            "",
            "- 轨迹由未来 ego pose 转换到当前自车坐标系得到。",
            "- 历史自车运动只使用当前帧之前的 ego pose，不包含未来答案。",
            "- 目标速度与 TTC 只使用当前及过去 annotation，不读取未来目标标注。",
            "- target_speed_mps 由未来轨迹生成，只作为 assistant 监督标签。",
            "- Risk 是根据交通参与者数量生成的 heuristic 弱监督标签，不是真实人工风险标注。",
            "- Action 也是由未来 ego pose 生成的 heuristic 弱监督标签，不是真实人工驾驶意图标注。",
            "- 数据按 scene 切分，训练场景与验证场景没有交集。",
            "",
        ]
    )
    return "\n".join(lines)


def build_dataset(args: argparse.Namespace) -> None:
    """执行完整数据转换并写出训练、验证和统计文件。"""
    if args.future_steps < 1:
        raise ValueError("future_steps 必须大于 0")
    val_ratio = 1.0 - args.train_ratio if args.train_ratio is not None else args.val_ratio
    if not 0.0 < val_ratio < 1.0:
        raise ValueError("训练/验证比例必须位于 0 和 1 之间")

    root = Path(args.nuscenes_root).expanduser().resolve()
    meta_root = root / args.version
    samples = load_json(meta_root / "sample.json")
    sample_data = load_json(meta_root / "sample_data.json")
    ego_poses = load_json(meta_root / "ego_pose.json")
    annotations = load_json(meta_root / "sample_annotation.json")
    instances = load_json(meta_root / "instance.json")
    categories = load_json(meta_root / "category.json")
    calibrated_sensor = load_json(meta_root / "calibrated_sensor.json")
    sensors = load_json(meta_root / "sensor.json")

    sample_by_token = {item["token"]: item for item in samples}
    pose_by_token = {item["token"]: item for item in ego_poses}
    annotation_by_token = {item["token"]: item for item in annotations}
    instance_by_token = {item["token"]: item for item in instances}
    category_by_token = {item["token"]: item for item in categories}
    annotations_by_sample: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for annotation in annotations:
        annotations_by_sample[annotation["sample_token"]].append(annotation)
    camera_by_sample = build_channel_lookup(sample_data, calibrated_sensor, sensors)

    rows: list[dict[str, Any]] = []
    skipped: Counter[str] = Counter()
    for sample in sorted(samples, key=lambda item: item["timestamp"]):
        current_camera = camera_by_sample.get(sample["token"], {}).get(args.camera)
        if current_camera is None:
            skipped["missing_camera"] += 1
            continue
        previous_samples = collect_previous_samples(sample, sample_by_token, args.history_steps)
        if previous_samples is None:
            skipped["insufficient_history"] += 1
            continue
        previous_cameras: list[dict[str, Any]] = []
        for previous_sample in previous_samples:
            camera = camera_by_sample.get(previous_sample["token"], {}).get(args.camera)
            if camera is None:
                previous_cameras = []
                break
            previous_cameras.append(camera)
        if len(previous_cameras) != args.history_steps:
            skipped["missing_camera"] += 1
            continue
        future_samples = collect_future_samples(sample, sample_by_token, args.future_steps)
        if future_samples is None:
            skipped["insufficient_future"] += 1
            continue

        future_cameras: list[dict[str, Any]] = []
        for future_sample in future_samples:
            camera = camera_by_sample.get(future_sample["token"], {}).get(args.camera)
            if camera is None:
                future_cameras = []
                break
            future_cameras.append(camera)
        if len(future_cameras) != args.future_steps:
            skipped["missing_camera"] += 1
            continue

        image_path = root / current_camera["filename"]
        if not image_path.exists():
            skipped["missing_image"] += 1
            continue

        current_pose = pose_by_token[current_camera["ego_pose_token"]]
        history_poses = [pose_by_token[camera["ego_pose_token"]] for camera in previous_cameras]
        history_motion = (
            build_history_motion(
                current_pose,
                history_poses,
                current_camera["timestamp"],
                [camera["timestamp"] for camera in previous_cameras],
            )
            if args.history_steps > 0
            else None
        )
        future_poses = [pose_by_token[camera["ego_pose_token"]] for camera in future_cameras]
        trajectory = build_future_trajectory(current_pose, future_poses)
        object_summary = summarize_objects(
            sample["token"],
            annotations_by_sample,
            instance_by_token,
            category_by_token,
            current_pose,
            args.max_objects,
            annotation_by_token,
            sample_by_token,
            float((history_motion or {}).get("current_speed_mps", 0.0)),
            args.include_object_motion,
        )
        rows.append(
            make_record(
                sample,
                image_path,
                trajectory,
                object_summary,
                args.future_steps,
                args.action_rule,
                history_motion,
                args.include_speed_target,
            )
        )

    if args.max_samples > 0:
        rows = rows[: args.max_samples]
    train_rows, val_rows, train_scenes, val_scenes = split_by_scene(
        rows,
        val_ratio,
        args.seed,
    )
    if train_scenes & val_scenes:
        raise RuntimeError("训练场景和验证场景发生重叠")

    raw_train_samples = len(train_rows)
    balance_info: dict[str, Any] = {"enabled": False}
    action_target_counts = parse_action_target_counts(args.action_target_counts_json)
    if args.balance_train and action_target_counts:
        raise ValueError("--balance-train 和 --action-target-counts-json 不能同时使用")
    if args.balance_train:
        train_rows, balance_info = balance_training_rows(
            train_rows,
            args.seed,
            args.balance_target_count,
        )
    elif action_target_counts:
        train_rows, balance_info = sample_training_rows_by_action_targets(
            train_rows,
            args.seed,
            action_target_counts,
        )

    output_dir = Path(args.output_dir)
    dump_jsonl(output_dir / "train.jsonl", train_rows)
    dump_jsonl(output_dir / "val.jsonl", val_rows)
    dump_json(
        output_dir / "drivevla_train.json",
        [to_llamafactory_row(row) for row in train_rows],
    )
    dump_json(
        output_dir / "drivevla_val.json",
        [to_llamafactory_row(row) for row in val_rows],
    )
    summary = {
        "nuscenes_root": str(root),
        "camera": args.camera,
        "future_steps": args.future_steps,
        "history_steps": args.history_steps,
        "action_rule": args.action_rule,
        "include_object_motion": args.include_object_motion,
        "include_speed_target": args.include_speed_target,
        "train_samples": len(train_rows),
        "raw_train_samples_before_balance": raw_train_samples,
        "val_samples": len(val_rows),
        "train_scenes": sorted(train_scenes),
        "val_scenes": sorted(val_scenes),
        "action_distribution": dict(Counter(row["metadata"]["action"] for row in rows)),
        "train_action_distribution": dict(Counter(row["metadata"]["action"] for row in train_rows)),
        "val_action_distribution": dict(Counter(row["metadata"]["action"] for row in val_rows)),
        "risk_distribution": dict(Counter(row["metadata"]["risk"] for row in rows)),
        "train_balance": balance_info,
        "object_motion_stats": {
            "nearest_object_count": sum(
                len(row["metadata"].get("nearest_objects", [])) for row in rows
            ),
            "motion_available_count": sum(
                actor.get("longitudinal_speed_mps") is not None
                for row in rows
                for actor in row["metadata"].get("nearest_objects", [])
            ),
            "ttc_available_count": sum(
                actor.get("ttc_s") is not None
                for row in rows
                for actor in row["metadata"].get("nearest_objects", [])
            ),
        },
        "target_speed_range_mps": (
            [
                min(row["ground_truth"]["target_speed_mps"] for row in rows),
                max(row["ground_truth"]["target_speed_mps"] for row in rows),
            ]
            if args.include_speed_target and rows
            else None
        ),
        "average_trajectory_path_length_m": round(
            mean(trajectory_path_length(row["ground_truth"]["trajectory"]) for row in rows),
            2,
        )
        if rows
        else 0.0,
        "skipped": dict(skipped),
    }
    dump_json(output_dir / "summary.json", summary)
    report = build_report(
        rows,
        train_rows,
        val_rows,
        train_scenes,
        val_scenes,
        skipped,
        args.action_rule,
        balance_info,
        args.history_steps,
        args.include_object_motion,
        args.include_speed_target,
    )
    (output_dir / "dataset_report.md").write_text(report, encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nuscenes-root", "--nuscenes_root", default="/home/pc/datasets/nuscenes")
    parser.add_argument("--version", default="v1.0-mini")
    parser.add_argument("--output-dir", "--output_dir", default="data/nuscenes_vla_sft")
    parser.add_argument("--camera", default="CAM_FRONT", choices=CAMERA_CHANNELS)
    parser.add_argument("--future-steps", "--future_steps", type=int, default=6)
    parser.add_argument("--val-ratio", "--val_ratio", type=float, default=0.1)
    parser.add_argument("--train-ratio", "--train_ratio", type=float, default=None)
    parser.add_argument("--max-samples", "--max_samples", type=int, default=-1)
    parser.add_argument("--max-objects", "--max_objects", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--history-steps", "--history_steps", type=int, default=0)
    parser.add_argument("--action-rule", "--action_rule", choices=("legacy", "v2", "v3"), default="legacy")
    parser.add_argument("--balance-train", "--balance_train", action="store_true")
    parser.add_argument("--balance-target-count", "--balance_target_count", type=int, default=0)
    parser.add_argument("--action-target-counts-json", "--action_target_counts_json", default="")
    parser.add_argument(
        "--include-object-motion",
        "--include_object_motion",
        action="store_true",
        help="使用目标过去标注生成纵向速度、相对速度和 TTC",
    )
    parser.add_argument(
        "--include-speed-target",
        "--include_speed_target",
        action="store_true",
        help="在 assistant JSON 中增加 target_speed_mps 监督",
    )
    return parser.parse_args()


if __name__ == "__main__":
    build_dataset(parse_args())
