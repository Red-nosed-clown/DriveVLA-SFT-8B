#!/usr/bin/env python3
"""DriveVLA CARLA waypoint 控制器测试。"""

from __future__ import annotations

import math
import unittest
from types import SimpleNamespace

from drivevla_carla.waypoint_controller import (
    ControllerConfig,
    WaypointController,
    validate_trajectory,
)
from drivevla_carla.prompt_builder import (
    EgoMotion,
    NearbyActor,
    SceneStats,
    build_online_prompt,
)
from drivevla_carla.scene_observer import normalize_angle_deg, world_delta_to_ego
from drivevla_carla.route_metrics import RoutePoint, RouteTracker, choose_branch


class WaypointControllerTest(unittest.TestCase):
    """覆盖方向转换、纵向控制和安全兜底。"""

    def setUp(self) -> None:
        self.config = ControllerConfig()
        self.controller = WaypointController(self.config)
        self.straight = [[2.0 * index, 0.0] for index in range(1, 7)]

    def test_straight_trajectory_accelerates_without_steering(self) -> None:
        command = self.controller.run_step(self.straight, current_speed_mps=1.0)
        self.assertAlmostEqual(command.steer, 0.0)
        self.assertGreater(command.throttle, 0.0)
        self.assertEqual(command.brake, 0.0)
        self.assertFalse(command.fallback)

    def test_positive_lateral_turns_left_in_carla(self) -> None:
        left = [[2.0, 0.2], [4.0, 0.6], [6.0, 1.2], [8.0, 2.0], [10.0, 3.0], [12.0, 4.0]]
        command = self.controller.run_step(left, current_speed_mps=4.0)
        self.assertLess(command.steer, 0.0)

    def test_negative_lateral_turns_right_in_carla(self) -> None:
        right = [[2.0, -0.2], [4.0, -0.6], [6.0, -1.2], [8.0, -2.0], [10.0, -3.0], [12.0, -4.0]]
        command = self.controller.run_step(right, current_speed_mps=4.0)
        self.assertGreater(command.steer, 0.0)

    def test_stop_action_brakes(self) -> None:
        command = self.controller.run_step(
            self.straight,
            current_speed_mps=5.0,
            action="STOP",
        )
        self.assertEqual(command.target_speed_mps, 0.0)
        self.assertEqual(command.throttle, 0.0)
        self.assertEqual(command.brake, 1.0)

    def test_slow_down_caps_target_speed(self) -> None:
        fast = [[6.0 * index, 0.0] for index in range(1, 7)]
        command = self.controller.run_step(
            fast,
            current_speed_mps=8.0,
            action="SLOW_DOWN",
        )
        self.assertEqual(command.target_speed_mps, self.config.slow_down_speed_mps)
        self.assertGreater(command.brake, 0.0)

    def test_timeout_uses_emergency_stop(self) -> None:
        command = self.controller.run_step(
            self.straight,
            current_speed_mps=3.0,
            prediction_age_s=4.0,
        )
        self.assertTrue(command.fallback)
        self.assertEqual(command.reason, "prediction_timeout")
        self.assertEqual(command.brake, 1.0)

    def test_non_finite_point_is_rejected(self) -> None:
        invalid = [point[:] for point in self.straight]
        invalid[2][1] = math.nan
        result = validate_trajectory(invalid, 0.0, self.config)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "non_finite_point")

    def test_large_lateral_value_is_rejected(self) -> None:
        invalid = [point[:] for point in self.straight]
        invalid[-1][1] = 20.0
        result = validate_trajectory(invalid, 0.0, self.config)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "lateral_out_of_bounds")

    def test_online_prompt_matches_v5_fields(self) -> None:
        prompt = build_online_prompt(
            SceneStats(vehicles=2, pedestrians=1, obstacles=0),
            [NearbyActor("vehicle.car", 8.0, 7.5, 1.0)],
            EgoMotion(
                history_steps=3,
                history_duration_s=1.5,
                history_speed_mps=[3.0, 3.5, 4.0],
                current_speed_mps=4.0,
                history_accel_mps2=0.67,
                history_yaw_delta_deg=2.0,
                history_forward_delta_m=5.0,
                history_lateral_delta_m=0.2,
            ),
        )
        self.assertIn("场景统计", prompt)
        self.assertIn("最近目标", prompt)
        self.assertIn("历史自车运动", prompt)
        self.assertIn("trajectory 必须包含未来 6 个", prompt)

    def test_world_delta_to_ego_uses_left_positive_lateral(self) -> None:
        """CARLA 世界坐标必须转换成训练数据使用的左正横向坐标。"""
        forward, lateral = world_delta_to_ego(10.0, -2.0, 0.0)
        self.assertAlmostEqual(forward, 10.0)
        self.assertAlmostEqual(lateral, 2.0)

    def test_angle_normalization_handles_wraparound(self) -> None:
        self.assertAlmostEqual(normalize_angle_deg(358.0), -2.0)

    def test_route_tracker_progress_is_monotonic(self) -> None:
        route = [RoutePoint(float(x), 0.0, 0.0, 0.0, float(x)) for x in range(0, 11, 2)]
        tracker = RouteTracker(route)
        forward = tracker.update(SimpleNamespace(x=6.1, y=0.0, z=0.0))
        backward = tracker.update(SimpleNamespace(x=1.0, y=0.0, z=0.0))
        self.assertEqual(forward["route_progress_m"], 6.0)
        self.assertEqual(backward["route_progress_m"], 6.0)
        self.assertAlmostEqual(forward["route_completion"], 0.6)

    def test_route_tracker_respects_physical_progress_bound(self) -> None:
        route = [RoutePoint(float(x), 0.0, 0.0, 0.0, float(x)) for x in range(0, 11, 2)]
        tracker = RouteTracker(route)
        state = tracker.update(
            SimpleNamespace(x=10.0, y=0.0, z=0.0),
            max_progress_m=3.0,
        )
        self.assertEqual(state["route_progress_m"], 2.0)

    def test_route_branch_command_selects_expected_yaw(self) -> None:
        def candidate(yaw: float) -> SimpleNamespace:
            return SimpleNamespace(
                transform=SimpleNamespace(rotation=SimpleNamespace(yaw=yaw))
            )

        candidates = [candidate(-45.0), candidate(2.0), candidate(50.0)]
        self.assertEqual(choose_branch(candidates, 0.0, "LEFT").transform.rotation.yaw, -45.0)
        self.assertEqual(choose_branch(candidates, 0.0, "STRAIGHT").transform.rotation.yaw, 2.0)
        self.assertEqual(choose_branch(candidates, 0.0, "RIGHT").transform.rotation.yaw, 50.0)


if __name__ == "__main__":
    unittest.main()
