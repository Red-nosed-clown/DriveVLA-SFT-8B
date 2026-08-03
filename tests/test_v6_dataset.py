#!/usr/bin/env python3
"""v6 目标运动与速度监督测试。"""

from __future__ import annotations

import json
import math
import unittest

from scripts.convert_nuscenes_to_qwen3vl import (
    infer_target_speed_mps,
    summarize_objects,
)
from scripts.parse_outputs import parse_model_output
from scripts.evaluate_drivevla import evaluate_rows


class V6DatasetTest(unittest.TestCase):
    """确认 v6 只用历史标注计算相对运动，并正确生成监督字段。"""

    def test_target_speed_uses_last_trajectory_segment(self) -> None:
        trajectory = [[1.0, 0.0], [2.0, 0.0], [3.5, 0.0]]
        self.assertEqual(infer_target_speed_mps(trajectory), 3.0)

    def test_target_speed_rejects_invalid_step_duration(self) -> None:
        with self.assertRaises(ValueError):
            infer_target_speed_mps([[1.0, 0.0]], step_duration_s=0.0)

    def test_object_motion_and_ttc_use_previous_annotation(self) -> None:
        previous = {
            "token": "ann_prev",
            "sample_token": "sample_prev",
            "translation": [8.0, 0.0, 0.0],
        }
        current = {
            "token": "ann_current",
            "sample_token": "sample_current",
            "instance_token": "instance",
            "prev": "ann_prev",
            "next": "future_token_must_not_be_read",
            "translation": [9.0, 0.0, 0.0],
        }
        summary = summarize_objects(
            "sample_current",
            {"sample_current": [current]},
            {"instance": {"category_token": "vehicle_category"}},
            {"vehicle_category": {"name": "vehicle.car"}},
            {"translation": [0.0, 0.0, 0.0], "rotation": [1.0, 0.0, 0.0, 0.0]},
            max_objects=8,
            annotation_by_token={"ann_prev": previous},
            sample_by_token={
                "sample_prev": {"timestamp": 0},
                "sample_current": {"timestamp": 500_000},
            },
            ego_speed_mps=5.0,
            include_object_motion=True,
        )
        actor = summary["nearest"][0]
        self.assertEqual(actor["longitudinal_speed_mps"], 2.0)
        self.assertEqual(actor["relative_longitudinal_speed_mps"], -3.0)
        self.assertEqual(actor["closing_speed_mps"], 3.0)
        self.assertTrue(math.isclose(actor["ttc_s"], 3.0))

    def test_ttc_is_omitted_for_lateral_actor(self) -> None:
        annotation = {
            "token": "ann",
            "sample_token": "sample",
            "instance_token": "instance",
            "prev": "",
            "translation": [10.0, 6.0, 0.0],
        }
        actor = summarize_objects(
            "sample",
            {"sample": [annotation]},
            {"instance": {"category_token": "vehicle_category"}},
            {"vehicle_category": {"name": "vehicle.car"}},
            {"translation": [0.0, 0.0, 0.0], "rotation": [1.0, 0.0, 0.0, 0.0]},
            max_objects=8,
            include_object_motion=True,
        )["nearest"][0]
        self.assertIsNone(actor["ttc_s"])

    def test_parser_preserves_valid_target_speed(self) -> None:
        prediction = {
            "action": "KEEP_LANE",
            "risk": "LOW",
            "trajectory": [[float(index), 0.0] for index in range(1, 7)],
            "reason": "道路通畅。",
            "target_speed_mps": 4.5,
        }
        parsed = parse_model_output(json.dumps(prediction, ensure_ascii=False))
        self.assertTrue(parsed["parse_success"])
        self.assertEqual(parsed["target_speed_mps"], 4.5)

    def test_evaluator_computes_target_speed_mae(self) -> None:
        prediction = {
            "action": "KEEP_LANE",
            "risk": "LOW",
            "trajectory": [[float(index), 0.0] for index in range(1, 7)],
            "reason": "道路通畅。",
            "target_speed_mps": 4.0,
        }
        rows = [
            {
                "prediction": json.dumps(prediction, ensure_ascii=False),
                "ground_truth": {**prediction, "target_speed_mps": 5.5},
            }
        ]
        metrics, _ = evaluate_rows(rows)
        self.assertEqual(metrics["target_speed_valid_rate"], 1.0)
        self.assertEqual(metrics["target_speed_mae_mps"], 1.5)


if __name__ == "__main__":
    unittest.main()
