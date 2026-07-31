#!/usr/bin/env python3
"""从 SFT 训练集抽取用于偏好数据挖掘的样本。

这个脚本只读取现有训练集，不生成模型答案。输出仍保持 DriveVLA JSONL 格式，
因此可以直接交给 ``infer_drivevla.py`` 运行冻结 SFT 模型推理。

抽样原则：
1. 只从 SFT train split 抽样。
2. 可以传入最终验证集，显式检查 sample 和 scene 都没有泄漏。
3. 默认提高 SLOW_DOWN 和转弯样本比例，但不复制任何样本。
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ACTIONS = ("KEEP_LANE", "SLOW_DOWN", "STOP", "TURN_LEFT", "TURN_RIGHT")
DEFAULT_WEIGHTS = {
    "KEEP_LANE": 0.20,
    "SLOW_DOWN": 0.30,
    "STOP": 0.10,
    "TURN_LEFT": 0.20,
    "TURN_RIGHT": 0.20,
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """读取 UTF-8 JSONL，并在损坏行出现时给出准确位置。"""
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path} 第 {line_number} 行不是合法 JSON：{exc}") from exc
    return rows


def save_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    """保存 JSONL，保留中文并自动创建输出目录。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def sample_id(row: dict[str, Any]) -> str:
    """返回稳定样本 ID。"""
    return str(row.get("id") or row.get("metadata", {}).get("sample_token") or "")


def scene_id(row: dict[str, Any]) -> str:
    """返回 scene token；缺失时返回空字符串供校验逻辑处理。"""
    return str(row.get("metadata", {}).get("scene_token") or "")


def action_name(row: dict[str, Any]) -> str:
    """优先读取 ground_truth，兼容只保留 metadata 的旧数据。"""
    return str(
        row.get("ground_truth", {}).get("action")
        or row.get("metadata", {}).get("action")
        or "UNKNOWN"
    )


def allocate_targets(max_samples: int, weights: dict[str, float]) -> dict[str, int]:
    """按权重分配整数目标数，并保证总数严格等于 max_samples。"""
    if max_samples <= 0:
        raise ValueError("max_samples 必须大于 0")
    total_weight = sum(max(value, 0.0) for value in weights.values())
    if total_weight <= 0:
        raise ValueError("抽样权重之和必须大于 0")

    raw = {
        action: max_samples * max(weights.get(action, 0.0), 0.0) / total_weight
        for action in ACTIONS
    }
    targets = {action: int(raw[action]) for action in ACTIONS}
    remainder = max_samples - sum(targets.values())
    order = sorted(ACTIONS, key=lambda action: raw[action] - targets[action], reverse=True)
    for action in order[:remainder]:
        targets[action] += 1
    return targets


def parse_targets(raw: str | None, max_samples: int) -> dict[str, int]:
    """解析自定义目标数量；未提供时使用项目默认权重。"""
    if raw is None:
        return allocate_targets(max_samples, DEFAULT_WEIGHTS)
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("--target-counts-json 必须是 JSON 对象")
    targets = {action: int(parsed.get(action, 0)) for action in ACTIONS}
    if any(value < 0 for value in targets.values()):
        raise ValueError("每类目标数量不能小于 0")
    return targets


def assert_no_final_validation_leakage(
    source_rows: list[dict[str, Any]],
    forbidden_rows: list[dict[str, Any]],
) -> None:
    """检查候选源数据与最终验证集的 sample/scene 均无交集。"""
    source_ids = {sample_id(row) for row in source_rows}
    forbidden_ids = {sample_id(row) for row in forbidden_rows}
    duplicate_ids = (source_ids & forbidden_ids) - {""}

    source_scenes = {scene_id(row) for row in source_rows}
    forbidden_scenes = {scene_id(row) for row in forbidden_rows}
    duplicate_scenes = (source_scenes & forbidden_scenes) - {""}
    if duplicate_ids or duplicate_scenes:
        raise ValueError(
            "检测到最终验证集泄漏："
            f"sample 重叠 {len(duplicate_ids)}，scene 重叠 {len(duplicate_scenes)}"
        )


def stratified_sample(
    rows: list[dict[str, Any]],
    targets: dict[str, int],
    seed: int,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """按 action 无放回抽样，不足的配额由其余类别补齐。"""
    random_generator = random.Random(seed)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[action_name(row)].append(row)
    for values in grouped.values():
        random_generator.shuffle(values)

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    shortages: dict[str, int] = {}
    requested_total = sum(targets.values())
    for action in ACTIONS:
        available = grouped.get(action, [])
        chosen = available[: targets[action]]
        selected.extend(chosen)
        selected_ids.update(sample_id(row) for row in chosen)
        if len(chosen) < targets[action]:
            shortages[action] = targets[action] - len(chosen)

    if len(selected) < requested_total:
        remaining = [row for row in rows if sample_id(row) not in selected_ids]
        random_generator.shuffle(remaining)
        selected.extend(remaining[: requested_total - len(selected)])

    random_generator.shuffle(selected)
    return selected, shortages


def build_report(
    source_path: Path,
    selected: list[dict[str, Any]],
    targets: dict[str, int],
    seed: int,
) -> dict[str, Any]:
    """生成机器可读抽样报告。"""
    return {
        "source_path": str(source_path.resolve()),
        "seed": seed,
        "target_counts": targets,
        "selected_samples": len(selected),
        "selected_scenes": len({scene_id(row) for row in selected} - {""}),
        "action_counts": dict(sorted(Counter(action_name(row) for row in selected).items())),
        "all_images_exist": all(Path(str(row.get("image", ""))).exists() for row in selected),
    }


def run(args: argparse.Namespace) -> None:
    """执行泄漏检查、分层抽样和报告写出。"""
    source_path = Path(args.source_path)
    rows = load_jsonl(source_path)
    if args.forbidden_data_path:
        assert_no_final_validation_leakage(
            rows,
            load_jsonl(Path(args.forbidden_data_path)),
        )

    targets = parse_targets(args.target_counts_json, args.max_samples)
    selected, shortages = stratified_sample(rows, targets, args.seed)
    if shortages:
        print(f"提示：部分动作样本不足，已从其他动作补齐：{shortages}")

    output_path = Path(args.output_path)
    save_jsonl(output_path, selected)
    report = build_report(source_path, selected, targets, args.seed)
    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"候选数据：{output_path}")


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-path",
        default="data/nuscenes_vla_sft_trainval_v5_history/train.jsonl",
    )
    parser.add_argument(
        "--forbidden-data-path",
        default="data/nuscenes_vla_sft_trainval_v5_history/val.jsonl",
    )
    parser.add_argument(
        "--output-path",
        default="data/drivevla_dpo/candidates.jsonl",
    )
    parser.add_argument(
        "--report-path",
        default="data/drivevla_dpo/candidate_report.json",
    )
    parser.add_argument("--max-samples", type=int, default=4000)
    parser.add_argument("--target-counts-json", default=None)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
