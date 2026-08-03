#!/usr/bin/env python3
"""汇总 CARLA 能力对齐场景结果并生成 Markdown 报告。"""

from __future__ import annotations

import argparse
import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


CAPABILITY_SCENARIOS = {
    "empty_straight",
    "natural_curve",
    "lead_slow",
    "lead_stop",
    "dense_traffic",
}


def percentage(value: float | None) -> str:
    """把 0 到 1 的比例格式化为百分数。"""
    return "-" if value is None else f"{100.0 * value:.2f}%"


def number(value: float | None, digits: int = 2) -> str:
    """格式化可能为空的浮点指标。"""
    return "-" if value is None else f"{value:.{digits}f}"


def infer_seed(path: Path, row: dict[str, Any]) -> int | None:
    """优先读取 summary.seed，并兼容旧结果文件名中的 seed。"""
    if row.get("seed") is not None:
        return int(row["seed"])
    match = re.search(r"seed(\d+)", path.stem)
    return int(match.group(1)) if match else None


def load_rows(
    results_dir: Path,
    planner: str = "qwen3vl",
) -> list[dict[str, Any]]:
    """只读取正式能力场景，排除历史 smoke 和路口导航实验。"""
    rows: list[dict[str, Any]] = []
    for path in sorted(results_dir.glob("*_summary.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        if row.get("planner") != planner or row.get("scenario") not in CAPABILITY_SCENARIOS:
            continue
        row["seed"] = infer_seed(path, row)
        row["source"] = str(path)
        prediction_count = int(row.get("prediction_count", 0))
        expected_count = int(row.get("scenario_expected_action_count", 0))
        row["expected_action_rate"] = (
            expected_count / prediction_count if prediction_count else None
        )
        rows.append(row)
    return rows


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """按场景聚合多 seed 指标，并保留总体动作分布。"""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    actions: Counter[str] = Counter()
    for row in rows:
        grouped[str(row["scenario"])].append(row)
        actions.update(row.get("action_counts", {}))

    scenario_metrics: dict[str, Any] = {}
    for scenario, items in sorted(grouped.items()):
        route_values = [item["route_completion"] for item in items]
        scenario_metrics[scenario] = {
            "runs": len(items),
            "seeds": sorted({item["seed"] for item in items if item["seed"] is not None}),
            "route_completion_mean": statistics.fmean(route_values),
            "route_completion_std": statistics.stdev(route_values) if len(route_values) > 1 else 0.0,
            "collision_run_rate": statistics.fmean(bool(item.get("collision_occurred")) for item in items),
            "lane_invasions_mean": statistics.fmean(item.get("lane_invasions", 0) for item in items),
            "fallback_rate_mean": statistics.fmean(item["fallback_rate"] for item in items),
            "hard_brake_rate_mean": statistics.fmean(item["hard_brake_rate"] for item in items),
            "latency_mean_s": statistics.fmean(item["latency_mean_s"] for item in items),
            "expected_action_rate_mean": statistics.fmean(
                item["expected_action_rate"]
                for item in items
                if item["expected_action_rate"] is not None
            ),
            "safe_stop_run_rate": statistics.fmean(bool(item.get("safe_stop_success")) for item in items),
        }
    return {
        "run_count": len(rows),
        "scenario_count": len(grouped),
        "unique_seeds": sorted({row["seed"] for row in rows if row["seed"] is not None}),
        "collision_runs": sum(bool(row.get("collision_occurred")) for row in rows),
        "collision_run_rate": statistics.fmean(
            bool(row.get("collision_occurred")) for row in rows
        ),
        "total_lane_invasions": sum(int(row.get("lane_invasions", 0)) for row in rows),
        "fallback_rate_mean": statistics.fmean(row["fallback_rate"] for row in rows),
        "hard_brake_rate_mean": statistics.fmean(row["hard_brake_rate"] for row in rows),
        "latency_mean_s": statistics.fmean(row["latency_mean_s"] for row in rows),
        "action_counts": dict(actions),
        "scenarios": scenario_metrics,
    }


def render_markdown(rows: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    """生成可供项目文档引用的中文实验报告。"""
    lines = [
        "# CARLA 能力场景评测汇总",
        "",
        f"- 有效运行：{summary['run_count']}",
        f"- 场景数：{summary['scenario_count']}",
        f"- Seed：{summary['unique_seeds']}",
        f"- 发生碰撞的运行：{summary['collision_runs']} / {summary['run_count']} "
        f"({percentage(summary['collision_run_rate'])})",
        f"- 车道侵入事件：{summary['total_lane_invasions']}",
        f"- 平均推理延迟：{number(summary['latency_mean_s'])} s",
        f"- 平均 fallback 占比：{percentage(summary['fallback_rate_mean'])}",
        "",
        "## 单次结果",
        "",
        "| Scenario | Seed | Route | Collision | Lane | Expected action | Fallback | Hard brake | Latency | Min lead | Safe stop |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {scenario} | {seed} | {route} | {collision} | {lane} | {expected} | "
            "{fallback} | {hard} | {latency}s | {lead} | {safe} |".format(
                scenario=row["scenario"],
                seed=row["seed"] if row["seed"] is not None else "-",
                route=percentage(row["route_completion"]),
                collision="YES" if row.get("collision_occurred") else "NO",
                lane=row.get("lane_invasions", 0),
                expected=percentage(row["expected_action_rate"]),
                fallback=percentage(row["fallback_rate"]),
                hard=percentage(row["hard_brake_rate"]),
                latency=number(row["latency_mean_s"]),
                lead=(
                    f"{number(row.get('minimum_lead_distance_m'))}m"
                    if row.get("minimum_lead_distance_m") is not None
                    else "-"
                ),
                safe=(
                    "YES" if row.get("safe_stop_success") else "NO"
                    if row.get("lead_vehicle")
                    else "-"
                ),
            )
        )

    lines.extend(
        [
            "",
            "## 分场景聚合",
            "",
            "| Scenario | Runs | Route mean±std | Collision runs | Lane mean | Expected action | Fallback | Hard brake | Latency |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for scenario, metrics in summary["scenarios"].items():
        lines.append(
            f"| {scenario} | {metrics['runs']} | "
            f"{percentage(metrics['route_completion_mean'])}±{percentage(metrics['route_completion_std'])} | "
            f"{percentage(metrics['collision_run_rate'])} | "
            f"{number(metrics['lane_invasions_mean'])} | "
            f"{percentage(metrics['expected_action_rate_mean'])} | "
            f"{percentage(metrics['fallback_rate_mean'])} | "
            f"{percentage(metrics['hard_brake_rate_mean'])} | "
            f"{number(metrics['latency_mean_s'])}s |"
        )

    lines.extend(["", "## 当前结论", ""])
    scenarios = summary["scenarios"]
    if curve := scenarios.get("natural_curve"):
        lines.append(
            f"- 自然弯道完成率为 {percentage(curve['route_completion_mean'])}±"
            f"{percentage(curve['route_completion_std'])}，但每次平均车道侵入 "
            f"{number(curve['lane_invasions_mean'])} 次：模型具备一定弯道响应，横向控制仍不稳定。"
        )
    if straight := scenarios.get("empty_straight"):
        lines.append(
            f"- 空旷直路完成率为 {percentage(straight['route_completion_mean'])}±"
            f"{percentage(straight['route_completion_std'])}，期望动作命中率仅 "
            f"{percentage(straight['expected_action_rate_mean'])}：不同 seed 下存在明显的过度停车和行为不稳定。"
        )
    if slow := scenarios.get("lead_slow"):
        lines.append(
            f"- 慢速前车期望动作命中率仅 {percentage(slow['expected_action_rate_mean'])}。"
            "当前输入没有显式前车相对速度或连续视觉帧，因此该工况同时暴露了观测信息不足，而不只是模型分类错误。"
        )
    if stop := scenarios.get("lead_stop"):
        lines.append(
            f"- 静止前车工况碰撞运行率为 {percentage(stop['collision_run_rate'])}，"
            f"安全停车成功率为 {percentage(stop['safe_stop_run_rate'])}，是当前最明确的安全短板。"
        )
    lines.extend(
        [
            f"- 总动作分布：`{json.dumps(summary['action_counts'], ensure_ascii=False)}`。",
            f"- 所有工况平均 fallback 占比为 {percentage(summary['fallback_rate_mean'])}，"
            "说明当前结果仍是 VLA 与控制器共同作用的闭环表现，不能归因于纯模型能力。",
            "- 已完成首轮 5 场景 × 5 seed 基准，但当前只覆盖单一地图、天气和参数组合，"
            "结论应表述为多 seed 稳定性评测，而不是完整域泛化。",
            "- `dense_traffic` 的期望动作集合较宽，命中率只能用于检查输出是否异常，不能作为精细决策能力指标。",
            "",
            "## 下一步",
            "",
            "1. 先保存本轮结果作为 v5 闭环基线，不通过规则后处理掩盖碰撞和过度停车。",
            "2. 对碰撞与零完成率运行做逐帧失败分析，定位模型动作、轨迹、fallback 和控制器各自责任。",
            "3. 构建 v6 时加入前车相对速度、TTC 或短时多帧信息，再测试 12/18/25 m 与 1/2/4 m/s 组合。",
            "4. v6 固定后再增加天气、地图和不同曲率，形成真正的域泛化矩阵。",
            "5. 始终分别报告纯 VLA 输出、fallback 使用率和最终闭环指标。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    """命令行入口。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", default="results/carla")
    parser.add_argument("--output-prefix", default="results/carla/capability_summary")
    args = parser.parse_args()
    rows = load_rows(Path(args.results_dir))
    if not rows:
        raise RuntimeError("没有找到 Qwen 能力场景 summary JSON")
    summary = aggregate(rows)
    prefix = Path(args.output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    json_path = prefix.with_suffix(".json")
    markdown_path = prefix.with_suffix(".md")
    json_path.write_text(
        json.dumps({"runs": rows, "aggregate": summary}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    markdown_path.write_text(render_markdown(rows, summary), encoding="utf-8")
    print(f"汇总 JSON：{json_path}")
    print(f"汇总报告：{markdown_path}")


if __name__ == "__main__":
    main()
