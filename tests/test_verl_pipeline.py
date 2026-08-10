#!/usr/bin/env python3
"""测试 VERL 数据筛选与 DriveVLA 分项奖励。"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "compat"))

from flash_attn.bert_padding import pad_input, unpad_input
from scripts.build_verl_drivevla_dataset import has_forward_hazard
from scripts.drivevla_verl_reward import compute_score


GT = {
    "action": "KEEP_LANE",
    "risk": "LOW",
    "trajectory": [[1, 0], [2, 0], [3, 0], [4, 0], [5, 0], [6, 0]],
    "reason": "测试",
    "target_speed_mps": 2.0,
}


class VerlPipelineTest(unittest.TestCase):
    def test_exact_answer_receives_high_reward(self) -> None:
        result = compute_score("drivevla_nuscenes_v6", json.dumps(GT), json.dumps(GT), {})
        self.assertGreater(result["score"], 0.95)
        self.assertEqual(result["parse_success"], 1.0)

    def test_unnecessary_stop_is_penalized(self) -> None:
        prediction = {**GT, "action": "STOP", "target_speed_mps": 0.0}
        result = compute_score(
            "drivevla_nuscenes_v6",
            json.dumps(prediction),
            json.dumps(GT),
            {"visible_forward_hazard": False},
        )
        self.assertLess(result["reward_penalty"], 0.0)
        self.assertLess(result["score"], 0.5)

    def test_direction_conflict_is_penalized(self) -> None:
        prediction = {**GT, "action": "TURN_LEFT"}
        result = compute_score("drivevla_nuscenes_v6", json.dumps(prediction), GT, {})
        self.assertLess(result["reward_penalty"], 0.0)

    def test_forward_hazard_uses_visible_current_objects(self) -> None:
        metadata = {"nearest_objects": [{"forward_m": 12.0, "lateral_m": 1.0}]}
        self.assertTrue(has_forward_hazard(metadata))
        metadata = {"nearest_objects": [{"forward_m": 12.0, "lateral_m": 5.0}]}
        self.assertFalse(has_forward_hazard(metadata))

    def test_padding_compat_round_trip(self) -> None:
        import torch

        values = torch.arange(12).reshape(2, 3, 2).float()
        mask = torch.tensor([[1, 1, 0], [0, 1, 1]])
        unpadded, indices, _, _ = unpad_input(values, mask)
        restored = pad_input(unpadded, indices, batch=2, seqlen=3)
        self.assertTrue(torch.equal(restored[mask.bool()], values[mask.bool()]))
        self.assertEqual(float(restored[~mask.bool()].sum()), 0.0)


if __name__ == "__main__":
    unittest.main()
