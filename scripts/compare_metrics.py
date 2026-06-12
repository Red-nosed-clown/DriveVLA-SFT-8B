#!/usr/bin/env python3
"""把基座模型和 QLoRA 模型指标汇总成一张 Markdown 对比表。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


METRICS = (
    ("parse_success_rate", "Parse Success", True),
    ("action_accuracy", "Action Accuracy", True),
    ("risk_accuracy", "Risk Accuracy", True),
    ("trajectory_valid_rate", "Trajectory Valid", True),
    ("ade", "ADE (m)", False),
    ("fde", "FDE (m)", False),
)


def load_metrics(path: Path) -> dict[str, Any]:
    """读取一份 evaluate_drivevla.py 生成的指标 JSON。"""
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def format_value(value: Any, percent: bool) -> str:
    """把比例显示为百分数，把距离显示为四位小数。"""
    if value is None:
        return "N/A"
    return f"{float(value) * 100:.2f}%" if percent else f"{float(value):.4f}"


def build_report(base: dict[str, Any], finetuned: dict[str, Any]) -> str:
    """生成可直接放入实验报告的基座/微调对比表。"""
    lines = [
        "# Base 与 QLoRA 对比",
        "",
        f"- 验证样本数：{base.get('num_samples', 0)}",
        "- ADE/FDE 只在成功解析出六点轨迹的样本上计算。",
        "",
        "| Metric | Base | QLoRA |",
        "|---|---:|---:|",
    ]
    for key, label, percent in METRICS:
        lines.append(
            f"| {label} | {format_value(base.get(key), percent)} "
            f"| {format_value(finetuned.get(key), percent)} |"
        )
    lines.extend(
        [
            "",
            f"- Base 失败样本：{base.get('failure_count', 0)}",
            f"- QLoRA 失败样本：{finetuned.get('failure_count', 0)}",
        ]
    )

    # 距离指标越低越好。只有 Base 指标为正数时才计算相对降幅，避免除零。
    for key, label in (("ade", "ADE"), ("fde", "FDE")):
        base_value = base.get(key)
        finetuned_value = finetuned.get(key)
        if isinstance(base_value, (int, float)) and base_value > 0 and isinstance(
            finetuned_value,
            (int, float),
        ):
            reduction = (base_value - finetuned_value) / base_value * 100
            lines.append(f"- {label} 相对降低：{reduction:.2f}%")
    lines.append("")
    return "\n".join(lines)


def main(args: argparse.Namespace) -> None:
    """加载两份指标并写出 Markdown 报告。"""
    base = load_metrics(Path(args.base_metrics))
    finetuned = load_metrics(Path(args.finetuned_metrics))
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_report(base, finetuned), encoding="utf-8")
    print(f"对比报告已生成：{output_path}")


def parse_args() -> argparse.Namespace:
    """解析指标路径和输出路径。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-metrics", required=True)
    parser.add_argument("--finetuned-metrics", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    main(parse_args())
