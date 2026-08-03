#!/usr/bin/env python3
"""运行 CARLA + Qwen3-VL 的第一版异步闭环驾驶实验。"""

from __future__ import annotations

import argparse
import json
import queue
import random
import statistics
import sys
import time
from collections import Counter
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from drivevla_carla.carla_adapter import command_to_vehicle_control, require_carla
from drivevla_carla.prompt_builder import build_online_prompt
from drivevla_carla.qwen_planner import PlannerPrediction, QwenDrivePlanner
from drivevla_carla.route_metrics import (
    RouteTracker,
    build_lane_route,
    route_contains_junction,
)
from drivevla_carla.scene_observer import (
    SceneObserver,
    normalize_angle_deg,
    world_delta_to_ego,
)
from drivevla_carla.waypoint_controller import ControllerConfig, WaypointController


class MockPlanner:
    """不加载模型的确定性规划器，仅用于验证 CARLA 闭环工程链路。"""

    def __init__(self, latency_s: float = 0.0) -> None:
        self.latency_s = latency_s

    def predict(self, image: Any, prompt_text: str) -> PlannerPrediction:
        del image, prompt_text
        started = time.perf_counter()
        if self.latency_s > 0.0:
            time.sleep(self.latency_s)
        trajectory = [[2.0 * index, 0.0] for index in range(1, 7)]
        parsed = {
            "parse_success": True,
            "parser": "mock",
            "action": "KEEP_LANE",
            "risk": "LOW",
            "trajectory": trajectory,
            "reason": "mock planner",
        }
        return PlannerPrediction(
            json.dumps(parsed),
            parsed,
            time.perf_counter() - started,
            time.monotonic(),
        )


def latest_queue_put(image_queue: queue.Queue, value: Any) -> None:
    """相机回调只保留最新帧，防止推理较慢时内存持续增长。"""
    try:
        image_queue.put_nowait(value)
    except queue.Full:
        try:
            image_queue.get_nowait()
        except queue.Empty:
            pass
        image_queue.put_nowait(value)


def carla_image_to_pil(image: Any) -> Any:
    """把 CARLA BGRA 原始缓冲区转换为 PIL RGB 图像。"""
    import numpy as np
    from PIL import Image

    bgra = np.frombuffer(image.raw_data, dtype=np.uint8).reshape(image.height, image.width, 4)
    rgb = bgra[:, :, :3][:, :, ::-1]
    return Image.fromarray(rgb.copy(), mode="RGB")


def predict_with_capture_time(
    planner: Any,
    image: Any,
    prompt: str,
    captured_at_s: float,
) -> tuple[PlannerPrediction, float]:
    """保留图像采集时间，使安全层能识别生成完成时已经过时的轨迹。"""
    return planner.predict(image, prompt), captured_at_s


def percentile(values: list[float], ratio: float) -> float | None:
    """计算无需第三方统计库的小样本百分位数。"""
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * ratio)))
    return ordered[index]


def build_controller_config(config: dict[str, Any]) -> ControllerConfig:
    """把 YAML 中 controller 与 safety 字段合并为控制器配置。"""
    allowed = set(ControllerConfig.__dataclass_fields__)
    values = {**config.get("controller", {}), **config.get("safety", {})}
    return ControllerConfig(**{key: value for key, value in values.items() if key in allowed})


def apply_capability_scenario(config: dict[str, Any], name: str) -> None:
    """把能力对齐场景名称展开为可复现的环境参数。"""
    profiles = {
        "empty_straight": {"require_curve": False, "npc": 0},
        "natural_curve": {"require_curve": True, "npc": 0},
        "lead_slow": {"require_curve": False, "npc": 0, "lead_speed": 2.0},
        "lead_stop": {"require_curve": False, "npc": 0, "lead_speed": 0.0},
        "dense_traffic": {"require_curve": False, "npc": 25},
    }
    if name not in profiles:
        raise ValueError(f"未知能力场景：{name}")
    profile = profiles[name]
    scenario = config.setdefault("scenario", {})
    scenario.update(
        {
            "name": name,
            "route_command": "STRAIGHT",
            "require_junction": False,
            "require_curve": profile["require_curve"],
        }
    )
    traffic = config.setdefault("traffic", {})
    traffic["enabled"] = profile["npc"] > 0
    traffic["npc_vehicles"] = profile["npc"]
    scenario["lead_vehicle_enabled"] = "lead_speed" in profile
    if "lead_speed" in profile:
        scenario["lead_vehicle_speed_mps"] = profile["lead_speed"]


def update_spectator_view(world: Any, ego: Any, config: dict[str, Any]) -> None:
    """把 CARLA GUI 观察者固定在 ego 后上方，形成第三人称跟随视角。"""
    spectator_cfg = config.get("spectator", {})
    if not spectator_cfg.get("enabled", True):
        return
    carla = require_carla()
    ego_transform = ego.get_transform()
    relative_location = carla.Location(
        x=float(spectator_cfg.get("x", -8.0)),
        y=float(spectator_cfg.get("y", 0.0)),
        z=float(spectator_cfg.get("z", 4.0)),
    )
    world_location = ego_transform.transform(relative_location)
    world.get_spectator().set_transform(
        carla.Transform(
            world_location,
            carla.Rotation(
                pitch=float(spectator_cfg.get("pitch", -15.0)),
                yaw=float(ego_transform.rotation.yaw),
                roll=0.0,
            ),
        )
    )


def build_route_fallback_trajectory(
    route_tracker: RouteTracker,
    ego: Any,
    point_count: int,
) -> list[list[float]]:
    """把 ego 前方车道中心点转换成六点局部轨迹。"""
    transform = ego.get_transform()
    location = transform.location
    nearest = min(
        range(len(route_tracker.route)),
        key=lambda index: (
            (route_tracker.route[index].x - float(location.x)) ** 2
            + (route_tracker.route[index].y - float(location.y)) ** 2
        ),
    )
    # 路线指标索引可能在立交或回环处受拓扑重叠影响；安全控制必须基于车辆
    # 当前几何位置重新锚定，不能直接复用指标索引。
    start = min(nearest + 1, len(route_tracker.route) - 1)
    selected = list(route_tracker.route[start : start + point_count])
    while selected and len(selected) < point_count:
        selected.append(selected[-1])
    trajectory: list[list[float]] = []
    for point in selected:
        forward, lateral = world_delta_to_ego(
            point.x - float(transform.location.x),
            point.y - float(transform.location.y),
            float(transform.rotation.yaw),
        )
        trajectory.append([forward, lateral])
    return trajectory


def run_route_fallback(
    controller: WaypointController,
    route_tracker: RouteTracker,
    ego: Any,
    speed_mps: float,
    control_dt_s: float,
) -> Any:
    """预测超时时沿模拟器车道中心受控减速，而不是立即满刹。"""
    trajectory = build_route_fallback_trajectory(
        route_tracker,
        ego,
        controller.config.trajectory_points,
    )
    command = controller.run_step(
        trajectory,
        speed_mps,
        action="SLOW_DOWN",
        prediction_age_s=0.0,
        control_dt_s=control_dt_s,
    )
    if command.fallback:
        if not getattr(controller, "_route_fallback_error_reported", False):
            print(
                f"[闭环] 车道 fallback 被安全层拒绝：{command.reason}，"
                f"trajectory={trajectory}",
                file=sys.stderr,
                flush=True,
            )
            controller._route_fallback_error_reported = True
        return controller.emergency_stop(f"route_fallback_{command.reason}")
    return replace(command, fallback=True, reason="route_fallback_timeout")


def spawn_ego_and_sensors(
    world: Any,
    config: dict[str, Any],
    image_queue: queue.Queue,
) -> tuple[Any, list[Any], list[Any], list[Any]]:
    """生成 ego、RGB 相机、碰撞传感器和车道侵入传感器。"""
    carla = require_carla()
    blueprints = world.get_blueprint_library()
    vehicle_bp = blueprints.find("vehicle.tesla.model3")
    spawn_points = world.get_map().get_spawn_points()
    if not spawn_points:
        raise RuntimeError("当前地图没有车辆出生点")
    scenario_cfg = config.get("scenario", {})
    if scenario_cfg.get("require_junction", False):
        junction_spawns = []
        for transform in spawn_points:
            preview = build_lane_route(
                world.get_map(),
                transform.location,
                float(scenario_cfg.get("junction_lookahead_m", 60.0)),
                step_m=4.0,
                route_command="STRAIGHT",
            )
            if route_contains_junction(preview):
                junction_spawns.append(transform)
        if not junction_spawns:
            raise RuntimeError("当前地图找不到前方包含路口的 ego 出生点")
        spawn_points = junction_spawns
    if scenario_cfg.get("require_curve", False):
        curve_spawns = []
        for transform in spawn_points:
            preview = build_lane_route(
                world.get_map(), transform.location, 45.0, step_m=3.0
            )
            yaw_delta = abs(
                normalize_angle_deg(preview[-1].yaw_deg - preview[0].yaw_deg)
            )
            if yaw_delta >= float(scenario_cfg.get("minimum_curve_yaw_deg", 15.0)):
                curve_spawns.append(transform)
        if not curve_spawns:
            raise RuntimeError("当前地图找不到满足曲率阈值的出生点")
        spawn_points = curve_spawns
    random.Random(int(config["simulation"]["seed"])).shuffle(spawn_points)
    ego = None
    for transform in spawn_points:
        ego = world.try_spawn_actor(vehicle_bp, transform)
        if ego is not None:
            break
    if ego is None:
        raise RuntimeError("无法在当前地图生成 ego 车辆")

    camera_cfg = config["camera"]
    camera_bp = blueprints.find("sensor.camera.rgb")
    camera_bp.set_attribute("image_size_x", str(camera_cfg["width"]))
    camera_bp.set_attribute("image_size_y", str(camera_cfg["height"]))
    camera_bp.set_attribute("fov", str(camera_cfg["fov"]))
    camera_bp.set_attribute("sensor_tick", str(camera_cfg["sensor_tick"]))
    camera = world.spawn_actor(
        camera_bp,
        carla.Transform(
            carla.Location(x=float(camera_cfg["x"]), z=float(camera_cfg["z"])),
        ),
        attach_to=ego,
    )
    camera.listen(
        lambda image: latest_queue_put(
            image_queue,
            (carla_image_to_pil(image), time.monotonic()),
        )
    )

    collision_events: list[Any] = []
    collision_bp = blueprints.find("sensor.other.collision")
    collision = world.spawn_actor(collision_bp, carla.Transform(), attach_to=ego)
    collision.listen(collision_events.append)

    lane_events: list[Any] = []
    lane_bp = blueprints.find("sensor.other.lane_invasion")
    lane_sensor = world.spawn_actor(lane_bp, carla.Transform(), attach_to=ego)
    lane_sensor.listen(lane_events.append)
    return ego, [camera, collision, lane_sensor], collision_events, lane_events


def spawn_npc_vehicles(
    client: Any,
    world: Any,
    ego: Any,
    config: dict[str, Any],
) -> tuple[list[Any], Any | None]:
    """生成由 Traffic Manager 控制的可复现 NPC 车辆流。"""
    traffic_cfg = config.get("traffic", {})
    if not traffic_cfg.get("enabled", False):
        return [], None
    port = int(config["server"]["traffic_manager_port"])
    traffic_manager = client.get_trafficmanager(port)
    traffic_manager.set_synchronous_mode(True)
    traffic_manager.set_random_device_seed(int(config["simulation"]["seed"]))
    traffic_manager.set_global_distance_to_leading_vehicle(
        float(traffic_cfg.get("following_distance_m", 2.5))
    )

    rng = random.Random(int(config["simulation"]["seed"]) + 1)
    blueprints = list(world.get_blueprint_library().filter("vehicle.*"))
    blueprints = [
        bp for bp in blueprints if bp.get_attribute("number_of_wheels").as_int() == 4
    ]
    spawn_points = world.get_map().get_spawn_points()
    rng.shuffle(spawn_points)
    minimum_distance = float(traffic_cfg.get("minimum_spawn_distance_m", 12.0))
    requested = int(traffic_cfg.get("npc_vehicles", 0))
    npc_actors: list[Any] = []
    ego_location = ego.get_location()
    for transform in spawn_points:
        if len(npc_actors) >= requested:
            break
        if transform.location.distance(ego_location) < minimum_distance:
            continue
        blueprint = rng.choice(blueprints)
        if blueprint.has_attribute("role_name"):
            blueprint.set_attribute("role_name", "autopilot")
        actor = world.try_spawn_actor(blueprint, transform)
        if actor is None:
            continue
        actor.set_autopilot(True, port)
        npc_actors.append(actor)
    print(f"[闭环] NPC 车辆：{len(npc_actors)}/{requested}", flush=True)
    return npc_actors, traffic_manager


def spawn_lead_vehicle(world: Any, ego: Any, config: dict[str, Any]) -> Any | None:
    """在 ego 同车道前方生成慢速或静止目标车。"""
    scenario = config.get("scenario", {})
    if not scenario.get("lead_vehicle_enabled", False):
        return None
    distance_m = float(scenario.get("lead_vehicle_distance_m", 18.0))
    waypoint = world.get_map().get_waypoint(ego.get_location())
    blueprint = world.get_blueprint_library().find("vehicle.audi.tt")
    if blueprint.has_attribute("role_name"):
        blueprint.set_attribute("role_name", "scenario_lead")
    carla = require_carla()
    lead = None
    for offset_m in (distance_m, distance_m + 2.0, distance_m + 4.0):
        candidates = waypoint.next(offset_m) if waypoint is not None else []
        if not candidates:
            continue
        target_waypoint = min(
            candidates,
            key=lambda item: abs(
                normalize_angle_deg(
                    float(item.transform.rotation.yaw)
                    - float(waypoint.transform.rotation.yaw)
                )
            ),
        )
        target = target_waypoint.transform
        spawn_transform = carla.Transform(
            carla.Location(
                x=float(target.location.x),
                y=float(target.location.y),
                z=float(target.location.z) + 0.5,
            ),
            target.rotation,
        )
        lead = world.try_spawn_actor(blueprint, spawn_transform)
        if lead is not None:
            break
    if lead is None:
        raise RuntimeError("目标车出生点被占用，请更换 seed 后重试")
    return lead


def update_lead_vehicle(lead: Any | None, config: dict[str, Any]) -> None:
    """保持场景目标车的设定速度。"""
    if lead is None:
        return
    carla = require_carla()
    speed = float(config["scenario"].get("lead_vehicle_speed_mps", 0.0))
    if speed <= 0.0:
        lead.apply_control(carla.VehicleControl(throttle=0.0, brake=1.0, hand_brake=True))
        lead.set_target_velocity(carla.Vector3D())
        return
    forward = lead.get_transform().get_forward_vector()
    lead.set_target_velocity(
        carla.Vector3D(x=forward.x * speed, y=forward.y * speed, z=0.0)
    )


def create_planner(config: dict[str, Any], mock: bool, mock_latency_s: float = 0.0) -> Any:
    """按命令行选择 mock 或真实 Qwen3-VL 规划器。"""
    if mock:
        return MockPlanner(mock_latency_s)
    planner_cfg = config["planner"]
    return QwenDrivePlanner(
        model_name_or_path=planner_cfg["model_name_or_path"],
        adapter_path=planner_cfg.get("adapter_path"),
        image_max_pixels=int(planner_cfg["image_max_pixels"]),
        max_new_tokens=int(planner_cfg["max_new_tokens"]),
        load_in_4bit=bool(planner_cfg["load_in_4bit"]),
        gpu_memory_fraction=float(planner_cfg.get("gpu_memory_fraction", 0.65)),
    )


def run(
    args: argparse.Namespace,
    planner_cache: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """执行一次闭环 episode，并返回可写入 JSON 的汇总指标。"""
    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    if args.scenario_name is not None:
        apply_capability_scenario(config, args.scenario_name)
    if args.seed is not None:
        config["simulation"]["seed"] = args.seed
    if args.route_command is not None:
        config.setdefault("scenario", {})["route_command"] = args.route_command
        config["scenario"]["name"] = f"intersection_{args.route_command.lower()}"
    print(f"[闭环] 已读取配置：{args.config}", flush=True)
    simulation = config["simulation"]
    scenario = config.get("scenario", {})
    route_command = str(scenario.get("route_command", "STRAIGHT")).upper()
    max_steps = args.max_steps or int(simulation["max_steps"])
    fixed_dt = float(simulation["fixed_delta_seconds"])
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    carla = require_carla()
    client = carla.Client(config["server"]["host"], int(config["server"]["rpc_port"]))
    client.set_timeout(float(config["server"].get("timeout_s", 120.0)))
    print("[闭环] 正在连接 CARLA 服务端", flush=True)
    world = client.get_world()
    current_town = world.get_map().name.rsplit("/", 1)[-1]
    if current_town != simulation["town"]:
        raise RuntimeError(
            f"服务端地图是 {current_town}，配置要求 {simulation['town']}。"
            "请按配置重启服务端，不要在运行中切图。"
        )

    original_settings = world.get_settings()
    settings = world.get_settings()
    settings.synchronous_mode = True
    settings.fixed_delta_seconds = fixed_dt
    world.apply_settings(settings)
    print(f"[闭环] 已启用同步模式，地图={current_town}，dt={fixed_dt:.3f}s", flush=True)

    image_queue: queue.Queue = queue.Queue(maxsize=1)
    controller = WaypointController(build_controller_config(config))
    observer = SceneObserver()
    planner = None
    executor: ThreadPoolExecutor | None = None
    future: Future | None = None
    latest_prediction: PlannerPrediction | None = None
    latest_capture_time_s: float | None = None
    actors: list[Any] = []
    rows: list[dict[str, Any]] = []
    latencies: list[float] = []
    fallback_steps = 0
    fallback_reasons: Counter[str] = Counter()
    action_counts: Counter[str] = Counter()
    next_submission_at_s = 0.0
    replan_interval_s = float(config["planner"].get("replan_interval_s", 0.5))
    traffic_manager = None
    route_tracker = None
    actual_steps = 0
    traveled_distance_m = 0.0
    previous_location = None
    goal_reached = False
    hard_brake_steps = 0
    lead_vehicle = None
    minimum_lead_distance_m = float("inf")
    stopped_for_lead = False
    latest_min_ttc_s = None
    observed_ttc_values: list[float] = []

    try:
        print("[闭环] 正在生成 ego、RGB 相机和碰撞传感器", flush=True)
        ego, sensors, collision_events, lane_events = spawn_ego_and_sensors(
            world,
            config,
            image_queue,
        )
        actors.extend([*sensors, ego])
        npc_actors, traffic_manager = spawn_npc_vehicles(client, world, ego, config)
        actors.extend(npc_actors)
        # 先推进一帧，让 UE4 完成相机和交通流 Vulkan 缓冲分配。随后再加载
        # Qwen，可避免 PyTorch 抢占显存后 CARLA 创建传感器缓冲失败。
        world.tick()
        route = build_lane_route(
            world.get_map(),
            ego.get_location(),
            float(simulation["route_length_m"]),
            float(simulation["route_step_m"]),
            route_command=route_command,
        )
        route_tracker = RouteTracker(route)
        lead_vehicle = spawn_lead_vehicle(world, ego, config)
        if lead_vehicle is not None:
            actors.append(lead_vehicle)
            update_lead_vehicle(lead_vehicle, config)
            world.tick()
            print(
                f"[闭环] 目标车：距离={scenario.get('lead_vehicle_distance_m', 18.0)}m，"
                f"速度={scenario.get('lead_vehicle_speed_mps', 0.0)}m/s",
                flush=True,
            )
        print("[闭环] actor 和 Vulkan 缓冲初始化完成", flush=True)
        cached_planner = planner_cache.get("planner") if planner_cache is not None else None
        if cached_planner is None:
            print(
                f"[闭环] 正在初始化 {'mock' if args.mock_planner else 'Qwen3-VL'} 规划器",
                flush=True,
            )
            planner = create_planner(config, args.mock_planner, args.mock_latency)
            if planner_cache is not None:
                planner_cache["planner"] = planner
        else:
            planner = cached_planner
            print("[闭环] 复用已加载的规划器", flush=True)
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="qwen-planner")
        # 模型加载可能持续数秒，加载前的相机帧已经失去规划价值。清空队列后，
        # 主循环只会使用下一次同步 tick 新采集的图像。
        while True:
            try:
                image_queue.get_nowait()
            except queue.Empty:
                break
        print("[闭环] 规划器加载完成，开始推进仿真", flush=True)
        # 车辆生成后可能从出生点高度落到路面；首个 tick 后再记录起点，避免把
        # 物理落位距离误算成闭环驾驶距离。
        start_location = None
        started_wall = time.perf_counter()

        for step in range(max_steps):
            tick_started = time.perf_counter()
            update_lead_vehicle(lead_vehicle, config)
            frame = world.tick()
            snapshot = world.get_snapshot()
            sim_time = float(snapshot.timestamp.elapsed_seconds)
            observer.update(ego, sim_time)
            current_location = ego.get_location()
            update_spectator_view(world, ego, config)
            if start_location is None:
                start_location = current_location
            if previous_location is not None:
                traveled_distance_m += previous_location.distance(current_location)
            previous_location = current_location
            route_state = route_tracker.update(
                current_location,
                max_progress_m=traveled_distance_m + float(simulation["route_step_m"]),
            )
            lead_distance = (
                current_location.distance(lead_vehicle.get_location())
                if lead_vehicle is not None
                else None
            )
            if lead_distance is not None:
                minimum_lead_distance_m = min(minimum_lead_distance_m, lead_distance)

            if future is not None and future.done():
                try:
                    latest_prediction, latest_capture_time_s = future.result()
                    latencies.append(latest_prediction.latency_s)
                    action_counts[str(latest_prediction.parsed.get("action", "UNKNOWN"))] += 1
                    # 给新轨迹短暂的执行时间，避免下一张图仍是启动前的静止状态。
                    next_submission_at_s = time.monotonic() + replan_interval_s
                except Exception as exc:  # 推理异常必须转成安全停车，不能终止 episode。
                    print(f"[闭环] 推理失败：{exc}", file=sys.stderr, flush=True)
                    latest_prediction = None
                future = None

            if future is None and time.monotonic() >= next_submission_at_s:
                try:
                    image, captured_at_s = image_queue.get_nowait()
                except queue.Empty:
                    image = None
                    captured_at_s = None
                if image is not None:
                    scene_stats, nearby = observer.observe_actors(world, ego)
                    current_ttc_values = [
                        float(actor.ttc_s) for actor in nearby if actor.ttc_s is not None
                    ]
                    latest_min_ttc_s = min(current_ttc_values) if current_ttc_values else None
                    observed_ttc_values.extend(current_ttc_values)
                    if str(scenario.get("name", "")).startswith("intersection_"):
                        command_text = {
                            "STRAIGHT": "通过前方路口直行",
                            "LEFT": "在前方路口左转",
                            "RIGHT": "在前方路口右转",
                        }.get(route_command, "沿当前车道行驶")
                        navigation = f"{command_text}并安全驶向目标点。"
                    else:
                        navigation = "安全沿当前可行驶车道行驶。"
                    prompt = build_online_prompt(
                        scene_stats,
                        nearby,
                        observer.ego_motion(),
                        navigation_instruction=navigation,
                        include_object_motion=(
                            str(config["planner"].get("prompt_version", "v5")) == "v6_safety"
                        ),
                        include_speed_target=(
                            str(config["planner"].get("prompt_version", "v5")) == "v6_safety"
                        ),
                    )
                    future = executor.submit(
                        predict_with_capture_time,
                        planner,
                        image,
                        prompt,
                        captured_at_s,
                    )

            motion = observer.ego_motion()
            if latest_prediction is None:
                command = controller.emergency_stop("waiting_for_prediction")
                prediction_age = None
                parsed = None
            else:
                prediction_age = time.monotonic() - float(latest_capture_time_s)
                parsed = latest_prediction.parsed
                if not parsed.get("parse_success") or parsed.get("trajectory") is None:
                    command = controller.emergency_stop("prediction_parse_failed")
                elif prediction_age > controller.config.prediction_timeout_s:
                    command = run_route_fallback(
                        controller,
                        route_tracker,
                        ego,
                        motion.current_speed_mps,
                        fixed_dt,
                    )
                else:
                    command = controller.run_step(
                        parsed["trajectory"],
                        motion.current_speed_mps,
                        action=str(parsed.get("action", "KEEP_LANE")),
                        prediction_age_s=prediction_age,
                        control_dt_s=fixed_dt,
                        predicted_target_speed_mps=parsed.get("target_speed_mps"),
                    )
            ego.apply_control(command_to_vehicle_control(command))
            if lead_distance is not None and lead_distance <= 12.0 and motion.current_speed_mps < 0.25:
                stopped_for_lead = True
            fallback_steps += int(command.fallback)
            hard_brake_steps += int(command.brake >= 0.99)
            if command.fallback:
                fallback_reasons[command.reason] += 1
            rows.append(
                {
                    "step": step,
                    "frame": frame,
                    "sim_time_s": sim_time,
                    "speed_mps": motion.current_speed_mps,
                    "prediction_age_s": prediction_age,
                    "prediction": parsed,
                    "control": asdict(command),
                    "collision_count": len(collision_events),
                    "lane_invasion_count": len(lane_events),
                    "lead_distance_m": lead_distance,
                    "minimum_ttc_s": latest_min_ttc_s,
                    **route_state,
                }
            )
            actual_steps = step + 1
            if step % 20 == 0:
                print(
                    f"[闭环] step={step}/{max_steps} speed={motion.current_speed_mps:.2f} "
                    f"fallback={command.fallback} reason={command.reason}",
                    flush=True,
                )
            goal_reached = (
                route_state["distance_to_goal_m"] <= float(simulation["goal_threshold_m"])
                or route_state["route_completion"] >= 0.999
            )
            if goal_reached and bool(simulation.get("stop_on_goal", True)):
                print(f"[闭环] 已到达路线终点，step={step}", flush=True)
                break
            if collision_events and bool(simulation.get("stop_on_collision", False)):
                print(f"[闭环] 检测到碰撞，step={step}", flush=True)
                break
            if bool(simulation.get("real_time", True)):
                time.sleep(max(0.0, fixed_dt - (time.perf_counter() - tick_started)))

        end_location = ego.get_location()
        distance = start_location.distance(end_location) if start_location is not None else 0.0
        expected_action = {
            "STRAIGHT": "KEEP_LANE",
            "LEFT": "TURN_LEFT",
            "RIGHT": "TURN_RIGHT",
        }.get(route_command, "UNKNOWN")
        opposite_action = {
            "LEFT": "TURN_RIGHT",
            "RIGHT": "TURN_LEFT",
        }.get(route_command)
        scenario_expected_actions = {
            "empty_straight": ["KEEP_LANE"],
            "natural_curve": ["KEEP_LANE", "TURN_LEFT", "TURN_RIGHT"],
            "lead_slow": ["SLOW_DOWN"],
            "lead_stop": ["STOP", "SLOW_DOWN"],
            "dense_traffic": ["KEEP_LANE", "SLOW_DOWN", "STOP"],
        }.get(str(scenario.get("name", "")), [])
        scenario_expected_count = sum(
            action_counts.get(action, 0) for action in scenario_expected_actions
        )
        safe_stop_success = bool(
            lead_vehicle is not None
            and stopped_for_lead
            and not collision_events
            and minimum_lead_distance_m >= float(scenario.get("safe_stop_distance_m", 5.0))
        )
        summary = {
            "planner": "mock" if args.mock_planner else "qwen3vl",
            "map": current_town,
            "scenario": str(scenario.get("name", "default")),
            "seed": int(simulation["seed"]),
            "route_command": route_command,
            "route_has_junction": route_contains_junction(route),
            "steps": actual_steps,
            "requested_steps": max_steps,
            "sim_duration_s": actual_steps * fixed_dt,
            "wall_duration_s": time.perf_counter() - started_wall,
            "displacement_m": float(distance),
            "traveled_distance_m": traveled_distance_m,
            "route_length_m": route_tracker.route_length_m,
            "route_progress_m": route_state["route_progress_m"],
            "route_completion": route_state["route_completion"],
            "distance_to_goal_m": route_state["distance_to_goal_m"],
            "goal_reached": goal_reached,
            "collisions": len(collision_events),
            "lane_invasions": len(lane_events),
            "npc_vehicles": len(npc_actors),
            "lead_vehicle": lead_vehicle is not None,
            "minimum_lead_distance_m": minimum_lead_distance_m
            if lead_vehicle is not None
            else None,
            "stopped_for_lead": stopped_for_lead,
            "safe_stop_success": safe_stop_success,
            "collision_occurred": bool(collision_events),
            "fallback_rate": fallback_steps / max(actual_steps, 1),
            "hard_brake_rate": hard_brake_steps / max(actual_steps, 1),
            "minimum_ttc_s": min(observed_ttc_values) if observed_ttc_values else None,
            "ttc_observation_count": len(observed_ttc_values),
            "fallback_reasons": dict(fallback_reasons),
            "prediction_count": len(latencies),
            "action_counts": dict(action_counts),
            # 这是 episode 级粗指标；尚未限定“车辆进入路口决策区”的时间窗。
            "expected_route_action": expected_action,
            "expected_action_count": action_counts.get(expected_action, 0),
            "opposite_turn_count": action_counts.get(opposite_action, 0)
            if opposite_action is not None
            else 0,
            "scenario_expected_actions": scenario_expected_actions,
            "scenario_expected_action_count": scenario_expected_count,
            "latency_mean_s": statistics.fmean(latencies) if latencies else None,
            "latency_p50_s": percentile(latencies, 0.50),
            "latency_p95_s": percentile(latencies, 0.95),
        }
        with output_path.open("w", encoding="utf-8") as file:
            for row in rows:
                file.write(json.dumps(row, ensure_ascii=False) + "\n")
        summary_path = output_path.with_name(f"{output_path.stem}_summary.json")
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
        print(f"逐帧日志：{output_path}", flush=True)
        print(f"汇总指标：{summary_path}", flush=True)
        return summary
    finally:
        if future is not None:
            future.cancel()
        if executor is not None:
            executor.shutdown(wait=True, cancel_futures=True)
        if traffic_manager is not None:
            try:
                traffic_manager.set_synchronous_mode(False)
            except RuntimeError:
                pass
        # actors 前三项固定为传感器。先停止回调，再通过服务端批量命令销毁，
        # 避免逐个 actor.destroy() 与同步 Traffic Manager 发生生命周期竞态。
        for actor in actors[:3]:
            try:
                if actor is not None:
                    actor.stop()
            except RuntimeError:
                pass
        destroy_commands = [carla.command.DestroyActor(actor.id) for actor in actors if actor is not None]
        if destroy_commands:
            try:
                client.apply_batch_sync(destroy_commands, True)
            except RuntimeError:
                # 服务端已经退出时无法完成批量清理，但仍需恢复 Python 侧状态。
                pass
        try:
            world.apply_settings(original_settings)
        except RuntimeError as exc:
            print(
                f"[闭环] 服务端已失联，跳过世界设置恢复：{exc}",
                file=sys.stderr,
                flush=True,
            )


def parse_args() -> argparse.Namespace:
    """解析闭环实验参数。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/carla_closed_loop.yaml")
    parser.add_argument("--output", default="results/carla/closed_loop_episode.jsonl")
    parser.add_argument("--max-steps", type=int, default=None)
    parser.add_argument("--mock-planner", action="store_true")
    parser.add_argument("--mock-latency", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument(
        "--scenario-name",
        choices=[
            "empty_straight",
            "natural_curve",
            "lead_slow",
            "lead_stop",
            "dense_traffic",
        ],
        default=None,
    )
    parser.add_argument(
        "--route-command",
        choices=["STRAIGHT", "LEFT", "RIGHT"],
        default=None,
    )
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
