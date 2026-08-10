#!/usr/bin/env python3
"""把 v6 DriveVLA JSONL 转换成 VERL 多模态 GRPO parquet。"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any

import datasets


DATA_SOURCE = "drivevla_nuscenes_v6"
# 单卡 GRPO 需要同时容纳训练模型与 vLLM；65k 仅用于验证一次真实反向更新。
IMAGE_MAX_PIXELS = 65_536


def has_forward_hazard(metadata: dict[str, Any]) -> bool:
    """只用当前帧可见目标判断前方是否存在直接障碍，不读取未来轨迹。"""
    return any(
        0.0 < float(actor.get("forward_m", -1.0)) <= 20.0
        and abs(float(actor.get("lateral_m", 99.0))) <= 3.0
        for actor in metadata.get("nearest_objects", [])
    )


def build_compact_prompt(metadata: dict[str, Any]) -> str:
    """构造无标签泄漏的紧凑观测，降低单卡 GRPO 的序列显存。"""
    nearest = [
        {
            "category": actor.get("category"),
            "forward_m": actor.get("forward_m"),
            "lateral_m": actor.get("lateral_m"),
            "closing_speed_mps": actor.get("closing_speed_mps"),
            "ttc_s": actor.get("ttc_s"),
        }
        for actor in metadata.get("nearest_objects", [])[:5]
    ]
    observation = {
        "object_counts": metadata.get("object_counts", {}),
        "nearest_objects": nearest,
        "history_motion": metadata.get("history_motion", {}),
        "motion_stats": metadata.get("motion_stats", {}),
    }
    return (
        "你是自动驾驶视觉语言动作模型。根据前视图像和观测预测未来驾驶动作、风险与轨迹。"
        "只输出合法 JSON，字段为 action、risk、trajectory、reason、target_speed_mps；"
        "trajectory 必须有 6 个 [forward_m, lateral_m] 点。\n"
        f"观测：{json.dumps(observation, ensure_ascii=False, separators=(',', ':'))}"
    )


def convert_row(row: dict[str, Any], split: str, index: int) -> dict[str, Any]:
    """生成 VERL 所需 prompt、图像、奖励答案和额外诊断字段。"""
    ground_truth = row["ground_truth"]
    metadata = row["metadata"]
    prompt_text = build_compact_prompt(metadata)
    image_path = str(Path(row["image"]).resolve())
    if not Path(image_path).is_file():
        raise FileNotFoundError(f"图片不存在：{image_path}")

    return {
        "data_source": DATA_SOURCE,
        "prompt": [{"role": "user", "content": f"<image>\n{prompt_text}"}],
        # 与 v6 SFT 正式训练保持相同的图像像素上限，避免原图在 VERL 中产生过多视觉 token。
        "images": [{"image": image_path, "max_pixels": IMAGE_MAX_PIXELS}],
        "ability": "drivevla_trajectory",
        "reward_model": {
            "style": "rule",
            # JSON 字符串可避免不同 pyarrow 版本改变嵌套结构字段类型。
            "ground_truth": json.dumps(ground_truth, ensure_ascii=False),
        },
        "extra_info": {
            "split": split,
            "index": index,
            "sample_token": metadata["sample_token"],
            "scene_token": metadata["scene_token"],
            "visible_forward_hazard": has_forward_hazard(metadata),
            "current_speed_mps": float(metadata["history_motion"]["current_speed_mps"]),
            "ground_truth_action": ground_truth["action"],
        },
    }


def select_rows(rows: list[dict[str, Any]], limit: int, seed: int) -> list[dict[str, Any]]:
    """优先保留容易暴露 STOP 自锁的低中速非停车样本，再补充随机样本。"""
    if limit <= 0 or limit >= len(rows):
        return rows
    rng = random.Random(seed)
    hard = [
        row
        for row in rows
        if row["ground_truth"]["action"] != "STOP"
        and 1.0 <= float(row["metadata"]["history_motion"]["current_speed_mps"]) <= 4.0
        and not has_forward_hazard(row["metadata"])
    ]
    others = [row for row in rows if row not in hard]
    rng.shuffle(hard)
    rng.shuffle(others)
    hard_count = min(len(hard), max(1, limit // 2))
    selected = hard[:hard_count] + others[: limit - hard_count]
    rng.shuffle(selected)
    return selected


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """读取非空 JSONL 行。"""
    return [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]


def write_eval_jsonl(rows: list[dict[str, Any]], path: Path) -> None:
    """保存与 VERL 完全同 prompt 的评估输入，供现有批量推理链路读取。"""
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            image_path = str(Path(row["image"]).resolve())
            sample = {
                "id": row["metadata"]["sample_token"],
                "image": image_path,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image", "image": image_path},
                            {"type": "text", "text": build_compact_prompt(row["metadata"])},
                        ],
                    }
                ],
                "ground_truth": row["ground_truth"],
                "metadata": row["metadata"],
            }
            handle.write(json.dumps(sample, ensure_ascii=False) + "\n")


def write_split(source: Path, output: Path, split: str, limit: int, seed: int) -> dict[str, Any]:
    """转换单个 split 并写入 parquet。"""
    rows = select_rows(load_jsonl(source), limit, seed)
    converted = [convert_row(row, split, index) for index, row in enumerate(rows)]
    output.parent.mkdir(parents=True, exist_ok=True)
    datasets.Dataset.from_list(converted).to_parquet(str(output))
    write_eval_jsonl(rows, output.with_name(f"{split}_eval.jsonl"))
    return {
        "samples": len(converted),
        "actions": dict(Counter(row["extra_info"]["ground_truth_action"] for row in converted)),
        "hard_negative_candidates": sum(
            not row["extra_info"]["visible_forward_hazard"]
            and row["extra_info"]["ground_truth_action"] != "STOP"
            and 1.0 <= row["extra_info"]["current_speed_mps"] <= 4.0
            for row in converted
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, default=Path("data/nuscenes_vla_sft_trainval_v6_safety"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/drivevla_verl/smoke"))
    parser.add_argument("--train-limit", type=int, default=16)
    parser.add_argument("--val-limit", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = {
        "data_source": DATA_SOURCE,
        "seed": args.seed,
        "train": write_split(
            args.source_dir / "train.jsonl",
            args.output_dir / "train.parquet",
            "train",
            args.train_limit,
            args.seed,
        ),
        "val": write_split(
            args.source_dir / "val.jsonl",
            args.output_dir / "val.parquet",
            "val",
            args.val_limit,
            args.seed + 1,
        ),
    }
    report_path = args.output_dir / "dataset_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"VERL 数据报告：{report_path}")


if __name__ == "__main__":
    main()
