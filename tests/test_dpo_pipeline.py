#!/usr/bin/env python3
"""DriveVLA DPO 数据与评估链路的轻量单元测试。"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from build_dpo_preferences import (
    build_rejected_text,
    classify_pair,
    score_prediction,
    split_by_scene,
)
from compare_drivevla_models import compare_rows
from register_dpo_dataset import preference_entry
from sample_dpo_candidates import allocate_targets, assert_no_final_validation_leakage


def answer(
    action: str,
    trajectory: list[list[float]],
    risk: str = "LOW",
) -> dict:
    """构造测试用结构化答案。"""
    return {
        "action": action,
        "risk": risk,
        "trajectory": trajectory,
        "reason": "测试",
    }


def prediction_row(row_id: str, model: str, ground_truth: dict, prediction: dict) -> dict:
    """构造比较脚本使用的预测行。"""
    return {
        "sample_id": row_id,
        "model": model,
        "ground_truth": ground_truth,
        "prediction": json.dumps(prediction, ensure_ascii=False),
    }


class DPOPipelineTest(unittest.TestCase):
    """覆盖偏好筛选、scene split 和结果对比的关键约束。"""

    def setUp(self) -> None:
        self.trajectory = [[1.0, 0.0], [2.0, 0.0], [3.0, 0.0], [4.0, 0.0], [5.0, 0.0], [6.0, 0.0]]

    def test_allocate_targets_keeps_total(self) -> None:
        targets = allocate_targets(
            17,
            {
                "KEEP_LANE": 0.2,
                "SLOW_DOWN": 0.3,
                "STOP": 0.1,
                "TURN_LEFT": 0.2,
                "TURN_RIGHT": 0.2,
            },
        )
        self.assertEqual(sum(targets.values()), 17)

    def test_slow_keep_confusion_is_selected(self) -> None:
        ground_truth = answer("SLOW_DOWN", self.trajectory)
        rejected = answer("KEEP_LANE", self.trajectory)
        diagnostics = score_prediction(
            ground_truth,
            json.dumps(rejected, ensure_ascii=False),
        )
        self.assertEqual(
            classify_pair(ground_truth, diagnostics),
            "slow_keep_confusion",
        )

    def test_exact_prediction_has_no_failure_category(self) -> None:
        ground_truth = answer("KEEP_LANE", self.trajectory)
        diagnostics = score_prediction(
            ground_truth,
            json.dumps(ground_truth, ensure_ascii=False),
        )
        self.assertIsNone(classify_pair(ground_truth, diagnostics))
        self.assertAlmostEqual(diagnostics["score"], 1.0)

    def test_isolated_action_negative_only_changes_action(self) -> None:
        ground_truth = answer("SLOW_DOWN", self.trajectory, risk="HIGH")
        rejected = answer(
            "KEEP_LANE",
            [[point[0] + 2.0, point[1] + 1.0] for point in self.trajectory],
            risk="LOW",
        )
        prediction = json.dumps(rejected, ensure_ascii=False)
        diagnostics = score_prediction(ground_truth, prediction)
        rejected_text, isolated_field = build_rejected_text(
            ground_truth,
            {"prediction": prediction},
            diagnostics,
            "slow_keep_confusion",
            "isolated_error",
        )
        isolated = json.loads(rejected_text)
        self.assertEqual(isolated_field, "action")
        self.assertEqual(isolated["action"], "KEEP_LANE")
        self.assertEqual(isolated["risk"], ground_truth["risk"])
        self.assertEqual(isolated["trajectory"], ground_truth["trajectory"])

    def test_isolated_trajectory_negative_keeps_other_fields(self) -> None:
        ground_truth = answer("TURN_LEFT", self.trajectory, risk="HIGH")
        predicted_trajectory = [
            [point[0], point[1] + 1.0] for point in self.trajectory
        ]
        rejected = answer("TURN_LEFT", predicted_trajectory, risk="LOW")
        prediction = json.dumps(rejected, ensure_ascii=False)
        diagnostics = score_prediction(ground_truth, prediction)
        rejected_text, isolated_field = build_rejected_text(
            ground_truth,
            {"prediction": prediction},
            diagnostics,
            "turn_geometry",
            "isolated_error",
        )
        isolated = json.loads(rejected_text)
        self.assertEqual(isolated_field, "trajectory")
        self.assertEqual(isolated["action"], ground_truth["action"])
        self.assertEqual(isolated["risk"], ground_truth["risk"])
        self.assertEqual(isolated["trajectory"], predicted_trajectory)

    def test_scene_split_has_no_overlap(self) -> None:
        rows = [
            {"metadata": {"scene_token": f"scene-{index // 2}"}}
            for index in range(20)
        ]
        train_rows, val_rows = split_by_scene(rows, 0.2, 42)
        train_scenes = {row["metadata"]["scene_token"] for row in train_rows}
        val_scenes = {row["metadata"]["scene_token"] for row in val_rows}
        self.assertFalse(train_scenes & val_scenes)
        self.assertTrue(train_rows)
        self.assertTrue(val_rows)

    def test_final_validation_leakage_is_rejected(self) -> None:
        source = [
            {
                "id": "train-1",
                "metadata": {"scene_token": "scene-shared"},
            }
        ]
        forbidden = [
            {
                "id": "val-1",
                "metadata": {"scene_token": "scene-shared"},
            }
        ]
        with self.assertRaises(ValueError):
            assert_no_final_validation_leakage(source, forbidden)

    def test_preference_entry_is_pairwise_multimodal(self) -> None:
        entry = preference_entry("train.json")
        self.assertTrue(entry["ranking"])
        self.assertEqual(entry["columns"]["chosen"], "chosen")
        self.assertEqual(entry["columns"]["images"], "images")

    def test_compare_rows_detects_trajectory_improvement(self) -> None:
        ground_truth = answer("KEEP_LANE", self.trajectory)
        baseline_trajectory = [[point[0] + 1.0, point[1]] for point in self.trajectory]
        baseline = [
            prediction_row(
                "sample-1",
                "sft",
                ground_truth,
                answer("KEEP_LANE", baseline_trajectory),
            )
        ]
        candidate = [
            prediction_row(
                "sample-1",
                "dpo",
                ground_truth,
                ground_truth,
            )
        ]
        report = compare_rows(baseline, candidate)
        self.assertEqual(report["paired_trajectory"]["candidate_wins"], 1)
        self.assertLess(report["candidate_metrics"]["ade"], report["baseline_metrics"]["ade"])


if __name__ == "__main__":
    unittest.main()
