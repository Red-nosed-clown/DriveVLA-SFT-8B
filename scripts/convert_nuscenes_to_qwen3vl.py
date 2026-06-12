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


def infer_action_token(trajectory: list[list[float]]) -> str:
    """根据最终轨迹点生成简化驾驶动作标签。"""
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
) -> dict[str, Any]:
    """统计交通参与者，并提取距离最近的目标作为可解释场景信息。"""
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
        nearest.append(
            {
                "category": category_name,
                "distance_m": round(math.hypot(forward, lateral), 2),
                "forward_m": round(forward, 2),
                "lateral_m": round(lateral, 2),
            }
        )
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
) -> dict[str, Any]:
    """构造自写脚本可读的 Qwen3-VL 多模态 SFT 样本。"""
    action = infer_action_token(trajectory)
    risk, risk_score = infer_risk_level(object_summary["counts"])
    answer = {
        "action": action,
        "risk": risk,
        "trajectory": trajectory,
        "reason": build_reason(action, risk),
    }
    prompt = (
        "你是自动驾驶视觉语言动作模型。根据前视相机图像和场景统计，"
        "预测自车未来驾驶动作、启发式风险等级和未来轨迹。"
        "只输出合法 JSON，不要输出 Markdown。"
        "字段必须为 action、risk、trajectory、reason；"
        f"trajectory 必须包含未来 {future_steps} 个 [forward_m, lateral_m] 点。\n"
        "驾驶指令：安全沿道路行驶。\n"
        f"场景统计：{json.dumps(object_summary['counts'], ensure_ascii=False)}\n"
        f"最近目标：{json.dumps(object_summary['nearest'], ensure_ascii=False)}"
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


def build_report(
    rows: list[dict[str, Any]],
    train_rows: list[dict[str, Any]],
    val_rows: list[dict[str, Any]],
    train_scenes: set[str],
    val_scenes: set[str],
    skipped: Counter[str],
) -> str:
    """生成可直接放入项目文档的数据集统计报告。"""
    action_counts = Counter(row["metadata"]["action"] for row in rows)
    risk_counts = Counter(row["metadata"]["risk"] for row in rows)
    average_path_length = (
        mean(trajectory_path_length(row["ground_truth"]["trajectory"]) for row in rows)
        if rows
        else 0.0
    )
    lines = [
        "# nuScenes-mini VLA 数据报告",
        "",
        "## 数据概览",
        "",
        f"- 成功转换：{len(rows)}",
        f"- 训练样本：{len(train_rows)}",
        f"- 验证样本：{len(val_rows)}",
        f"- 训练场景：{len(train_scenes)}",
        f"- 验证场景：{len(val_scenes)}",
        f"- 轨迹点数：{len(rows[0]['ground_truth']['trajectory']) if rows else 0}",
        f"- 平均未来轨迹路程：{average_path_length:.2f} 米",
        f"- 缺失图片：{skipped['missing_image']}",
        f"- scene 末尾未来帧不足：{skipped['insufficient_future']}",
        f"- 缺失相机关键帧：{skipped['missing_camera']}",
        "",
        "## Action 分布",
        "",
    ]
    lines.extend(f"- {name}: {action_counts.get(name, 0)}" for name in VALID_ACTIONS)
    lines.extend(["", "## Risk 分布", ""])
    lines.extend(f"- {name}: {risk_counts.get(name, 0)}" for name in VALID_RISKS)
    lines.extend(
        [
            "",
            "## 标签说明",
            "",
            "- 轨迹由未来 ego pose 转换到当前自车坐标系得到。",
            "- Risk 是根据交通参与者数量生成的 heuristic 弱监督标签，不是真实人工风险标注。",
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
        future_poses = [pose_by_token[camera["ego_pose_token"]] for camera in future_cameras]
        trajectory = build_future_trajectory(current_pose, future_poses)
        object_summary = summarize_objects(
            sample["token"],
            annotations_by_sample,
            instance_by_token,
            category_by_token,
            current_pose,
            args.max_objects,
        )
        rows.append(
            make_record(
                sample,
                image_path,
                trajectory,
                object_summary,
                args.future_steps,
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
        "train_samples": len(train_rows),
        "val_samples": len(val_rows),
        "train_scenes": sorted(train_scenes),
        "val_scenes": sorted(val_scenes),
        "action_distribution": dict(Counter(row["metadata"]["action"] for row in rows)),
        "risk_distribution": dict(Counter(row["metadata"]["risk"] for row in rows)),
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
    return parser.parse_args()


if __name__ == "__main__":
    build_dataset(parse_args())
