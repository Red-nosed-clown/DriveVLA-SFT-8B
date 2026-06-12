#!/usr/bin/env python3
"""把评估阶段筛选出的失败样本整理为 Markdown 文档。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from parse_outputs import load_jsonl


def json_block(value: Any) -> str:
    """把 Python 对象格式化为 Markdown JSON 代码块。"""
    return "```json\n" + json.dumps(value, ensure_ascii=False, indent=2) + "\n```"


def infer_possible_reason(row: dict[str, Any]) -> str:
    """根据错误组合生成保守的排查方向。

    输入：
        row：evaluate_drivevla.py 输出的一条失败样本。

    输出：
        一句“可能原因”，只作为工程排查线索，不声称是确定因果。

    为什么这样做：
        自动指标告诉我们哪里错了，但初学者还需要知道下一步应查看数据不均衡、
        输出格式还是轨迹回归。这里使用透明规则生成线索，避免编造模型内部原因。
    """
    error_types = set(row.get("error_types", []))
    ground_truth = row.get("ground_truth") or {}
    prediction = row.get("parsed_prediction") or {}

    if "Invalid output format" in error_types:
        return "模型没有稳定遵守枚举值或 JSON 结构，需要加强格式监督或约束解码。"
    if (
        "Action error" in error_types
        and ground_truth.get("action") == "TURN_LEFT"
        and prediction.get("action") in {"KEEP_LANE", "STOP"}
    ):
        return "左转样本较少，模型可能偏向训练集中更常见的 KEEP_LANE 或 STOP。"
    if "Large ADE" in error_types or "Large FDE" in error_types:
        return "轨迹形状或速度尺度预测不准；若同时动作错误，离散决策错误会进一步放大轨迹误差。"
    if "Risk error" in error_types:
        return "Risk 是数量规则生成的弱标签，模型可能没有学到规则阈值或受到类别不均衡影响。"
    if "Action error" in error_types:
        return "当前帧视觉和统计信息不足以区分相近动作，也可能受到动作类别不均衡影响。"
    return "需要结合原图、场景统计和相邻帧继续人工检查。"


def build_failure_report(rows: list[dict[str, Any]], max_samples: int) -> str:
    """生成失败分析文档，优先展示轨迹误差较大的样本。"""
    ordered = sorted(
        rows,
        key=lambda row: (
            row.get("ade") is not None,
            row.get("ade") or 0.0,
            len(row.get("error_types", [])),
        ),
        reverse=True,
    )
    lines = [
        "# DriveVLA 失败案例分析",
        "",
        f"- 失败样本总数：{len(rows)}",
        f"- 展示样本数：{min(len(rows), max_samples)}",
        "",
    ]
    for index, row in enumerate(ordered[:max_samples], start=1):
        lines.extend(
            [
                f"## {index}. {row.get('sample_id')}",
                "",
                f"- 图片：`{row.get('image')}`",
                f"- 错误类型：{', '.join(row.get('error_types', []))}",
                f"- ADE：{row.get('ade')}",
                f"- FDE：{row.get('fde')}",
                f"- 可能原因：{infer_possible_reason(row)}",
                "",
                "### Ground Truth",
                "",
                json_block(row.get("ground_truth")),
                "",
                "### Parsed Prediction",
                "",
                json_block(row.get("parsed_prediction")),
                "",
                "### Raw Prediction",
                "",
                "```text",
                str(row.get("prediction", "")),
                "```",
                "",
            ]
        )
    return "\n".join(lines)


def analyze(args: argparse.Namespace) -> None:
    """读取失败 JSONL 并写出 Markdown。"""
    rows = load_jsonl(Path(args.failure_path))
    output_path = Path(args.output_md)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        build_failure_report(rows, args.max_samples),
        encoding="utf-8",
    )
    print(f"失败分析已保存：{output_path}")


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--failure-path", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--max-samples", type=int, default=20)
    return parser.parse_args()


if __name__ == "__main__":
    analyze(parse_args())
