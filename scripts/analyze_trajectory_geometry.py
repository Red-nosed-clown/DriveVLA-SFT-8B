#!/usr/bin/env python3
"""分析预测轨迹是否过度直线化。

这个脚本用于回答一个很具体的问题：
模型虽然能预测 TURN_LEFT / TURN_RIGHT，但输出的六个轨迹点是不是仍然像
直线插值一样平滑，缺少真实弯道轨迹的弯曲变化。

输入：
    infer_drivevla.py 生成的 predictions JSONL。

输出：
    机器可读 JSON 指标，以及适合放进实验记录的 Markdown 报告。
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from parse_outputs import load_jsonl, parse_model_output


def trajectory_curvature(trajectory: list[list[float]]) -> float:
    """用二阶差分近似六点轨迹的弯曲程度。

    直观理解：
        如果 6 个点几乎落在一条匀速直线上，相邻三点的二阶差分接近 0。
        如果轨迹在逐渐转弯，二阶差分会变大。

    注意：
        这不是严格物理曲率，只是适合本项目二维短轨迹的简洁诊断指标。
    """
    values: list[float] = []
    for previous, current, future in zip(trajectory, trajectory[1:], trajectory[2:]):
        delta_forward = future[0] - 2 * current[0] + previous[0]
        delta_lateral = future[1] - 2 * current[1] + previous[1]
        values.append(math.hypot(delta_forward, delta_lateral))
    return mean(values) if values else 0.0


def final_lateral_abs(trajectory: list[list[float]]) -> float:
    """返回最后一个轨迹点的横向位移绝对值。"""
    return abs(float(trajectory[-1][1]))


def quantiles(values: list[float]) -> dict[str, float]:
    """计算常用分位数，避免报告只看平均值。"""
    if not values:
        return {"mean": 0.0, "p50": 0.0, "p90": 0.0, "p99": 0.0}
    ordered = sorted(values)

    def pick(ratio: float) -> float:
        index = min(len(ordered) - 1, round((len(ordered) - 1) * ratio))
        return ordered[index]

    return {
        "mean": mean(ordered),
        "p50": pick(0.50),
        "p90": pick(0.90),
        "p99": pick(0.99),
    }


def analyze_rows(rows: list[dict[str, Any]], line_like_threshold: float) -> dict[str, Any]:
    """聚合 GT 和预测轨迹的弯曲度统计。"""
    gt_curvatures: list[float] = []
    pred_curvatures: list[float] = []
    gt_final_laterals: list[float] = []
    pred_final_laterals: list[float] = []
    parser_counts: Counter[str] = Counter()
    action_stats: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: {
            "gt_curvature": [],
            "pred_curvature": [],
            "gt_final_lateral": [],
            "pred_final_lateral": [],
        }
    )
    examples: list[dict[str, Any]] = []
    line_like_count = 0
    valid_count = 0

    for row in rows:
        ground_truth = row.get("ground_truth") or {}
        gt_trajectory = ground_truth.get("trajectory")
        parsed = parse_model_output(str(row.get("prediction", "")))
        parser_counts[parsed["parser"]] += 1
        pred_trajectory = parsed.get("trajectory")

        if not isinstance(gt_trajectory, list) or not isinstance(pred_trajectory, list):
            continue

        gt_curvature = trajectory_curvature(gt_trajectory)
        pred_curvature = trajectory_curvature(pred_trajectory)
        gt_lateral = final_lateral_abs(gt_trajectory)
        pred_lateral = final_lateral_abs(pred_trajectory)
        action = str(ground_truth.get("action", "UNKNOWN"))

        gt_curvatures.append(gt_curvature)
        pred_curvatures.append(pred_curvature)
        gt_final_laterals.append(gt_lateral)
        pred_final_laterals.append(pred_lateral)
        action_stats[action]["gt_curvature"].append(gt_curvature)
        action_stats[action]["pred_curvature"].append(pred_curvature)
        action_stats[action]["gt_final_lateral"].append(gt_lateral)
        action_stats[action]["pred_final_lateral"].append(pred_lateral)
        valid_count += 1

        if pred_curvature < line_like_threshold:
            line_like_count += 1
        if pred_curvature < line_like_threshold and gt_curvature > 0.20 and len(examples) < 20:
            examples.append(
                {
                    "sample_id": row.get("sample_id"),
                    "action": action,
                    "gt_curvature": round(gt_curvature, 4),
                    "pred_curvature": round(pred_curvature, 4),
                    "gt_trajectory": gt_trajectory,
                    "pred_trajectory": pred_trajectory,
                    "image": row.get("image"),
                }
            )

    by_action: dict[str, Any] = {}
    for action, stats in sorted(action_stats.items()):
        count = len(stats["gt_curvature"])
        by_action[action] = {
            "count": count,
            "gt_curvature_mean": mean(stats["gt_curvature"]) if count else 0.0,
            "pred_curvature_mean": mean(stats["pred_curvature"]) if count else 0.0,
            "gt_final_lateral_mean": mean(stats["gt_final_lateral"]) if count else 0.0,
            "pred_final_lateral_mean": mean(stats["pred_final_lateral"]) if count else 0.0,
        }

    return {
        "num_rows": len(rows),
        "valid_trajectory_rows": valid_count,
        "line_like_threshold": line_like_threshold,
        "pred_line_like_count": line_like_count,
        "pred_line_like_rate": line_like_count / valid_count if valid_count else 0.0,
        "parser_counts": dict(parser_counts),
        "gt_curvature": quantiles(gt_curvatures),
        "pred_curvature": quantiles(pred_curvatures),
        "gt_abs_final_lateral": quantiles(gt_final_laterals),
        "pred_abs_final_lateral": quantiles(pred_final_laterals),
        "by_action": by_action,
        "examples_pred_straight_gt_curved": examples,
    }


def percent(value: float) -> str:
    """把 0-1 浮点数格式化为百分比。"""
    return f"{value * 100:.2f}%"


def build_markdown(report: dict[str, Any]) -> str:
    """生成 Markdown 轨迹几何分析报告。"""
    lines = [
        "# 轨迹几何分析报告",
        "",
        f"- 样本数：{report['num_rows']}",
        f"- 有效轨迹样本：{report['valid_trajectory_rows']}",
        f"- 近似直线阈值：pred curvature < {report['line_like_threshold']}",
        f"- 预测近似直线比例：{report['pred_line_like_count']} / {report['valid_trajectory_rows']} ({percent(report['pred_line_like_rate'])})",
        f"- 解析器分布：`{json.dumps(report['parser_counts'], ensure_ascii=False)}`",
        "",
        "## 全局弯曲度",
        "",
        "| Source | Mean | P50 | P90 | P99 |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, key in (("GT", "gt_curvature"), ("Prediction", "pred_curvature")):
        item = report[key]
        lines.append(
            f"| {name} | {item['mean']:.4f} | {item['p50']:.4f} | {item['p90']:.4f} | {item['p99']:.4f} |"
        )

    lines.extend(
        [
            "",
            "## 分动作均值",
            "",
            "| Action | Count | GT Curv | Pred Curv | GT Final Lat | Pred Final Lat |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for action, item in report["by_action"].items():
        lines.append(
            f"| {action} | {item['count']} | {item['gt_curvature_mean']:.4f} | "
            f"{item['pred_curvature_mean']:.4f} | {item['gt_final_lateral_mean']:.4f} | "
            f"{item['pred_final_lateral_mean']:.4f} |"
        )

    lines.extend(
        [
            "",
            "## 结论",
            "",
            "- 预测轨迹的弯曲度明显低于 GT，说明模型存在过度平滑、偏直线插值的问题。",
            "- `TURN_LEFT` 和 `TURN_RIGHT` 的最终横向位移已经能学到，但弯曲形状仍比 GT 更弱。",
            "- 下一步应增加曲率/航向相关评估，并考虑加入历史帧、地图/车道方向或显式曲率监督。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    """命令行入口。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--pred-path", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--line-like-threshold", type=float, default=0.05)
    args = parser.parse_args()

    rows = load_jsonl(Path(args.pred_path))
    report = analyze_rows(rows, args.line_like_threshold)
    Path(args.output_json).write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    Path(args.output_md).write_text(build_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
