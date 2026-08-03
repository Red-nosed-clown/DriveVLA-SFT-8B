#!/usr/bin/env python3
"""连接 CARLA、切换地图并完成最小同步模式冒烟测试。"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any


# 直接执行 ``python scripts/carla_smoke_client.py`` 时，Python 默认只把
# scripts 目录加入搜索路径。显式加入项目根目录，兼容 7B 软链接和 8B 实际路径。
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from drivevla_carla.carla_adapter import require_carla


def destroy_safely(actor: Any | None) -> None:
    """销毁测试 actor，避免下次运行残留。"""
    if actor is not None and actor.is_alive:
        actor.destroy()


def log_stage(message: str) -> None:
    """把阶段信息写到 stderr，stdout 仍保持为可解析的 JSON。"""
    print(f"[CARLA smoke] {message}", file=sys.stderr, flush=True)


def run_smoke(
    host: str,
    port: int,
    town: str,
    ticks: int,
    seed: int,
    timeout: float,
) -> dict:
    """运行最小 CARLA 服务端连接、车辆生成和同步 tick 测试。"""
    carla = require_carla()
    client = carla.Client(host, port)
    client.set_timeout(timeout)
    log_stage(f"连接 {host}:{port}，超时上限 {timeout:.0f} 秒")
    server_version = client.get_server_version()
    client_version = client.get_client_version()
    log_stage(f"连接成功，服务端版本 {server_version}")
    world = client.get_world()
    current_town = world.get_map().name.rsplit("/", 1)[-1]
    if current_town != town:
        log_stage(f"当前地图是 {current_town}，开始加载 {town}")
        world = client.load_world(town)
    else:
        log_stage(f"服务端已经运行在 {town}，跳过重复加载")
    log_stage(f"地图加载完成：{world.get_map().name}")
    original_settings = world.get_settings()
    vehicle = None

    try:
        settings = world.get_settings()
        settings.synchronous_mode = True
        settings.fixed_delta_seconds = 0.05
        world.apply_settings(settings)
        log_stage("已进入 20 Hz 同步模式，开始生成测试车辆")

        blueprint_library = world.get_blueprint_library()
        candidates = blueprint_library.filter("vehicle.tesla.model3")
        if not candidates:
            candidates = blueprint_library.filter("vehicle.*")
        if not candidates:
            raise RuntimeError("CARLA 地图中没有可用车辆 blueprint")

        spawn_points = world.get_map().get_spawn_points()
        if not spawn_points:
            raise RuntimeError("当前地图没有车辆出生点")
        random.Random(seed).shuffle(spawn_points)
        for transform in spawn_points:
            vehicle = world.try_spawn_actor(candidates[0], transform)
            if vehicle is not None:
                break
        if vehicle is None:
            raise RuntimeError("所有出生点都无法生成测试车辆")

        log_stage(f"已生成 {vehicle.type_id}，开始执行 {ticks} 个同步 tick")
        frame_start = world.tick()
        vehicle.apply_control(carla.VehicleControl(throttle=0.25))
        frame_end = frame_start
        for _ in range(ticks):
            frame_end = world.tick()
        location = vehicle.get_location()
        log_stage("同步 tick 测试通过，正在清理测试车辆")
        return {
            "server_version": server_version,
            "client_version": client_version,
            "map": world.get_map().name,
            "vehicle": vehicle.type_id,
            "ticks": ticks,
            "frame_start": frame_start,
            "frame_end": frame_end,
            "final_location": {
                "x": location.x,
                "y": location.y,
                "z": location.z,
            },
        }
    finally:
        destroy_safely(vehicle)
        world.apply_settings(original_settings)


def main() -> None:
    """命令行入口。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2000)
    parser.add_argument("--town", default="Town10HD_Opt")
    parser.add_argument("--ticks", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="单次 CARLA RPC 的超时秒数；首次加载地图通常需要几十秒",
    )
    args = parser.parse_args()
    print(
        json.dumps(
            run_smoke(
                args.host,
                args.port,
                args.town,
                args.ticks,
                args.seed,
                args.timeout,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
