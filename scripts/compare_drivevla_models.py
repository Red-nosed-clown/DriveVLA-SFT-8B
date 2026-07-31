#!/usr/bin/env python3
"""对两个 DriveVLA 模型执行同样本、同口径的成对比较。

这个脚本用于回答 DPO 是否真的优于 SFT，而不是只比较两个总 loss。它会校验
sample ID 完全一致，并输出总体指标、分动作 Precision/Recall/F1、每类 ADE/FDE、
转弯终点航向误差，以及逐样本轨迹胜负数量。
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from evaluate_drivevla import displacement_errors, evaluate_rows
from parse_outputs import load_jsonl, parse_model_output


ACTIONS = ("KEEP_LANE", "SLOW_DOWN", "STOP", "TURN_LEFT", "TURN_RIGHT")
TURN_ACTIONS = {"TURN_LEFT", "TURN_RIGHT"}


def ensure_parsed(row: dict[str, Any]) -> dict[str, Any]:
    """返回解析结果；输入是原始 predictions 时现场解析。"""
    parsed = row.get("parsed_prediction")
    if isinstance(parsed, dict):
        return parsed
    return parse_model_output(str(row.get("prediction", "")))


def endpoint_heading_error(
    ground_truth: list[list[float]],
    prediction: list[list[float]],
) -> float:
    """计算终点方向角误差，单位为度。"""
    gt_heading = math.degrees(math.atan2(ground_truth[-1][1], ground_truth[-1][0]))
    pred_heading = math.degrees(math.atan2(prediction[-1][1], prediction[-1][0]))
    return abs((pred_heading - gt_heading + 180.0) % 360.0 - 180.0)


def per_action_metrics(rows: list[dict[str, Any]]) -> dict[str, dict[str, float | int]]:
    """计算每个 GT action 的分类和轨迹指标。"""
    gt_counts: Counter[str] = Counter()
    pred_counts: Counter[str] = Counter()
    correct_counts: Counter[str] = Counter()
    values: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: {
            "ade": [],
            "fde": [],
            "final_lateral_error": [],
            "heading_error_deg": [],
        }
    )

    for row in rows:
        ground_truth = row.get("ground_truth", {})
        parsed = ensure_parsed(row)
        gt_action = str(ground_truth.get("action", "UNKNOWN"))
        pred_action = str(parsed.get("action", "UNKNOWN"))
        gt_counts[gt_action] += 1
        pred_counts[pred_action] += 1
        if gt_action == pred_action:
            correct_counts[gt_action] += 1

        gt_trajectory = ground_truth.get("trajectory")
        pred_trajectory = parsed.get("trajectory")
        if not (
            isinstance(gt_trajectory, list)
            and isinstance(pred_trajectory, list)
            and len(gt_trajectory) == len(pred_trajectory) == 6
        ):
            continue
        ade, fde = displacement_errors(gt_trajectory, pred_trajectory)
        values[gt_action]["ade"].append(ade)
        values[gt_action]["fde"].append(fde)
        values[gt_action]["final_lateral_error"].append(
            abs(pred_trajectory[-1][1] - gt_trajectory[-1][1])
        )
        if gt_action in TURN_ACTIONS:
            values[gt_action]["heading_error_deg"].append(
                endpoint_heading_error(gt_trajectory, pred_trajectory)
            )

    result: dict[str, dict[str, float | int]] = {}
    for action in ACTIONS:
        precision = (
            correct_counts[action] / pred_counts[action] if pred_counts[action] else 0.0
        )
        recall = correct_counts[action] / gt_counts[action] if gt_counts[action] else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        result[action] = {
            "count": gt_counts[action],
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "ade": mean(values[action]["ade"]) if values[action]["ade"] else 0.0,
            "fde": mean(values[action]["fde"]) if values[action]["fde"] else 0.0,
            "final_lateral_error": (
                mean(values[action]["final_lateral_error"])
                if values[action]["final_lateral_error"]
                else 0.0
            ),
            "heading_error_deg": (
                mean(values[action]["heading_error_deg"])
                if values[action]["heading_error_deg"]
                else 0.0
            ),
        }
    return result


def confusion_matrix(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    """生成 GT 为行、Prediction 为列的动作混淆矩阵。"""
    matrix = {action: Counter() for action in ACTIONS}
    for row in rows:
        gt_action = str(row.get("ground_truth", {}).get("action", "UNKNOWN"))
        pred_action = str(ensure_parsed(row).get("action", "UNKNOWN"))
        if gt_action in matrix:
            matrix[gt_action][pred_action] += 1
    columns = list(ACTIONS) + ["UNKNOWN"]
    return {
        gt_action: {pred_action: matrix[gt_action][pred_action] for pred_action in columns}
        for gt_action in ACTIONS
    }


def paired_trajectory_comparison(
    baseline_by_id: dict[str, dict[str, Any]],
    candidate_by_id: dict[str, dict[str, Any]],
    tolerance: float,
) -> dict[str, Any]:
    """逐样本比较 ADE，统计 DPO 改善、持平和退化数量。"""
    wins = ties = losses = 0
    ade_deltas: list[float] = []
    for row_id in sorted(baseline_by_id):
        baseline = baseline_by_id[row_id]
        candidate = candidate_by_id[row_id]
        ground_truth = baseline.get("ground_truth", {}).get("trajectory")
        baseline_trajectory = ensure_parsed(baseline).get("trajectory")
        candidate_trajectory = ensure_parsed(candidate).get("trajectory")
        if not all(
            isinstance(value, list) and len(value) == 6
            for value in (ground_truth, baseline_trajectory, candidate_trajectory)
        ):
            continue
        baseline_ade, _ = displacement_errors(ground_truth, baseline_trajectory)
        candidate_ade, _ = displacement_errors(ground_truth, candidate_trajectory)
        delta = baseline_ade - candidate_ade
        ade_deltas.append(delta)
        if delta > tolerance:
            wins += 1
        elif delta < -tolerance:
            losses += 1
        else:
            ties += 1
    return {
        "candidate_wins": wins,
        "ties": ties,
        "candidate_losses": losses,
        "mean_ade_improvement_m": mean(ade_deltas) if ade_deltas else 0.0,
        "tolerance_m": tolerance,
    }


def index_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """按 sample_id 建立索引，并拒绝空 ID 或重复 ID。"""
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        row_id = str(row.get("sample_id", ""))
        if not row_id or row_id in indexed:
            raise ValueError(f"发现空 sample_id 或重复 sample_id：{row_id!r}")
        indexed[row_id] = row
    return indexed


def compare_rows(
    baseline_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    tolerance: float = 0.01,
) -> dict[str, Any]:
    """校验同集并计算完整对比结果。"""
    baseline_by_id = index_rows(baseline_rows)
    candidate_by_id = index_rows(candidate_rows)
    if baseline_by_id.keys() != candidate_by_id.keys():
        missing = sorted(baseline_by_id.keys() - candidate_by_id.keys())
        extra = sorted(candidate_by_id.keys() - baseline_by_id.keys())
        raise ValueError(
            "两个模型的评估样本不一致："
            f"candidate 缺少 {len(missing)}，多出 {len(extra)}"
        )

    ordered_ids = sorted(baseline_by_id)
    baseline_ordered = [baseline_by_id[row_id] for row_id in ordered_ids]
    candidate_ordered = [candidate_by_id[row_id] for row_id in ordered_ids]
    baseline_metrics, _ = evaluate_rows(baseline_ordered)
    candidate_metrics, _ = evaluate_rows(candidate_ordered)

    metric_deltas: dict[str, float] = {}
    for key in (
        "parse_success_rate",
        "action_accuracy",
        "risk_accuracy",
        "trajectory_valid_rate",
        "ade",
        "fde",
    ):
        baseline_value = baseline_metrics.get(key)
        candidate_value = candidate_metrics.get(key)
        if isinstance(baseline_value, (int, float)) and isinstance(
            candidate_value, (int, float)
        ):
            metric_deltas[key] = candidate_value - baseline_value

    return {
        "num_samples": len(ordered_ids),
        "baseline_model": baseline_metrics.get("model", "baseline"),
        "candidate_model": candidate_metrics.get("model", "candidate"),
        "baseline_metrics": baseline_metrics,
        "candidate_metrics": candidate_metrics,
        "candidate_minus_baseline": metric_deltas,
        "baseline_per_action": per_action_metrics(baseline_ordered),
        "candidate_per_action": per_action_metrics(candidate_ordered),
        "baseline_confusion": confusion_matrix(baseline_ordered),
        "candidate_confusion": confusion_matrix(candidate_ordered),
        "paired_trajectory": paired_trajectory_comparison(
            baseline_by_id,
            candidate_by_id,
            tolerance,
        ),
    }


def percent(value: float) -> str:
    """格式化百分数。"""
    return f"{value * 100:.2f}%"


def build_markdown(report: dict[str, Any]) -> str:
    """生成便于提交和答辩的 Markdown 对比报告。"""
    baseline = report["baseline_metrics"]
    candidate = report["candidate_metrics"]
    lines = [
        "# DriveVLA SFT 与 DPO 对比报告",
        "",
        f"- 样本数：{report['num_samples']}",
        f"- Baseline：`{report['baseline_model']}`",
        f"- Candidate：`{report['candidate_model']}`",
        "",
        "## 总体指标",
        "",
        "| Metric | SFT | DPO | DPO - SFT |",
        "|---|---:|---:|---:|",
    ]
    for label, key, is_percent in (
        ("Parse Success", "parse_success_rate", True),
        ("Action Accuracy", "action_accuracy", True),
        ("Risk Accuracy", "risk_accuracy", True),
        ("Trajectory Valid", "trajectory_valid_rate", True),
        ("ADE (m)", "ade", False),
        ("FDE (m)", "fde", False),
    ):
        baseline_value = float(baseline[key])
        candidate_value = float(candidate[key])
        delta = candidate_value - baseline_value
        formatter = percent if is_percent else lambda value: f"{value:.4f}"
        lines.append(
            f"| {label} | {formatter(baseline_value)} | "
            f"{formatter(candidate_value)} | {formatter(delta)} |"
        )

    lines.extend(
        [
            "",
            "## 分动作结果",
            "",
            "| Action | SFT F1 | DPO F1 | SFT ADE | DPO ADE | SFT FDE | DPO FDE |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for action in ACTIONS:
        baseline_action = report["baseline_per_action"][action]
        candidate_action = report["candidate_per_action"][action]
        lines.append(
            f"| {action} | {percent(float(baseline_action['f1']))} | "
            f"{percent(float(candidate_action['f1']))} | "
            f"{float(baseline_action['ade']):.4f} | "
            f"{float(candidate_action['ade']):.4f} | "
            f"{float(baseline_action['fde']):.4f} | "
            f"{float(candidate_action['fde']):.4f} |"
        )

    paired = report["paired_trajectory"]
    lines.extend(
        [
            "",
            "## 成对轨迹比较",
            "",
            f"- DPO 改善：{paired['candidate_wins']} 条",
            f"- 基本持平：{paired['ties']} 条",
            f"- DPO 退化：{paired['candidate_losses']} 条",
            f"- 平均 ADE 改善：{paired['mean_ade_improvement_m']:.4f} m",
            "",
            "## 判定",
            "",
        ]
    )
    action_delta = report["candidate_minus_baseline"].get("action_accuracy", 0.0)
    ade_delta = report["candidate_minus_baseline"].get("ade", 0.0)
    fde_delta = report["candidate_minus_baseline"].get("fde", 0.0)
    if action_delta >= 0 and ade_delta <= 0 and fde_delta <= 0:
        lines.append("- DPO 在动作与轨迹主指标上没有出现相互牺牲，可以作为有效改进版本。")
    else:
        lines.append("- DPO 至少有一项主指标退化，需要结合分动作结果调整偏好数据配比。")
    return "\n".join(lines) + "\n"


def run(args: argparse.Namespace) -> None:
    """读取两个预测文件并写出 JSON/Markdown 报告。"""
    report = compare_rows(
        load_jsonl(Path(args.baseline_path)),
        load_jsonl(Path(args.candidate_path)),
        args.ade_tolerance,
    )
    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    output_md.write_text(build_markdown(report), encoding="utf-8")
    print(build_markdown(report))


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-path", required=True)
    parser.add_argument("--candidate-path", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--ade-tolerance", type=float, default=0.01)
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
