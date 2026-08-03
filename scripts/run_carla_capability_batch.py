#!/usr/bin/env python3
"""复用一次 Qwen 加载，批量运行 CARLA 能力场景和多个 seed。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_carla_closed_loop import run
from scripts.summarize_carla_scenarios import aggregate, load_rows, render_markdown


DEFAULT_SCENARIOS = [
    "empty_straight",
    "natural_curve",
    "lead_slow",
    "lead_stop",
    "dense_traffic",
]


def refresh_report(results_dir: Path, output_prefix: Path, planner: str) -> None:
    """每轮结束后刷新汇总，长任务中断时也能保留已有结果。"""
    rows = load_rows(results_dir, planner=planner)
    summary = aggregate(rows)
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    output_prefix.with_suffix(".json").write_text(
        json.dumps({"runs": rows, "aggregate": summary}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    output_prefix.with_suffix(".md").write_text(
        render_markdown(rows, summary),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    """解析批量实验参数。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/carla_closed_loop.yaml")
    parser.add_argument("--results-dir", default="results/carla/generalization")
    parser.add_argument("--scenarios", nargs="+", default=DEFAULT_SCENARIOS)
    parser.add_argument("--seeds", nargs="+", type=int, default=[7, 21, 42, 84, 123])
    parser.add_argument("--max-steps", type=int, default=300)
    parser.add_argument("--mock-planner", action="store_true")
    parser.add_argument("--mock-latency", type=float, default=0.0)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> None:
    """按场景和 seed 顺序运行；模型只在第一轮加载。"""
    args = parse_args()
    unknown = sorted(set(args.scenarios) - set(DEFAULT_SCENARIOS))
    if unknown:
        raise ValueError(f"不支持的场景：{unknown}")
    results_dir = Path(args.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    planner_cache: dict[str, object] = {}
    total = len(args.scenarios) * len(args.seeds)
    completed = 0

    for scenario in args.scenarios:
        for seed in args.seeds:
            completed += 1
            stem = f"qwen_{scenario}_seed{seed}"
            if args.mock_planner:
                stem = f"mock_{scenario}_seed{seed}"
            output_path = results_dir / f"{stem}.jsonl"
            summary_path = output_path.with_name(f"{output_path.stem}_summary.json")
            if summary_path.exists() and not args.overwrite:
                print(f"[批量] {completed}/{total} 已存在，跳过：{summary_path}", flush=True)
                continue

            print(
                f"\n[批量] {completed}/{total} scenario={scenario} seed={seed}",
                flush=True,
            )
            episode_args = SimpleNamespace(
                config=args.config,
                output=str(output_path),
                max_steps=args.max_steps,
                mock_planner=args.mock_planner,
                mock_latency=args.mock_latency,
                seed=seed,
                scenario_name=scenario,
                route_command=None,
            )
            try:
                run(episode_args, planner_cache=planner_cache)
            except Exception as exc:
                failure_path = results_dir / "batch_failure.json"
                failure_path.write_text(
                    json.dumps(
                        {
                            "scenario": scenario,
                            "seed": seed,
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                print(f"[批量] 失败并停止：{exc}", file=sys.stderr, flush=True)
                print(f"[批量] 失败记录：{failure_path}", file=sys.stderr, flush=True)
                raise

            refresh_report(
                results_dir,
                results_dir / "capability_generalization_summary",
                planner="mock" if args.mock_planner else "qwen3vl",
            )

    print("\n[批量] 全部完成", flush=True)
    print(
        f"[批量] 报告：{results_dir / 'capability_generalization_summary.md'}",
        flush=True,
    )


if __name__ == "__main__":
    main()
