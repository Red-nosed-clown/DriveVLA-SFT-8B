#!/usr/bin/env python3
"""检查 DriveVLA 闭环运行所需的 CARLA 环境。"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import socket
import subprocess
from pathlib import Path
from typing import Any

import yaml


def run_command(command: list[str]) -> tuple[bool, str]:
    """执行只读检查命令，并返回成功状态和合并后的输出。"""
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    output = (result.stdout + result.stderr).strip()
    return result.returncode == 0, output


def port_is_listening(host: str, port: int) -> bool:
    """检查 CARLA RPC 端口是否已经接受连接。"""
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except OSError:
        return False


def load_config(path: Path) -> dict[str, Any]:
    """读取 YAML 配置。"""
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def x11_socket_path(display: str) -> Path | None:
    """把 ``DISPLAY=:1`` 转换为对应的 X11 Unix socket。"""
    if not display.startswith(":"):
        return None
    display_number = display[1:].split(".", maxsplit=1)[0]
    if not display_number.isdigit():
        return None
    return Path(f"/tmp/.X11-unix/X{display_number}")


def check_environment(config_path: Path) -> tuple[dict[str, Any], bool]:
    """执行检查并返回机器可读报告与总体状态。"""
    config = load_config(config_path)
    server = config["server"]
    image = str(server["image"])
    host = str(server["host"])
    port = int(server["rpc_port"])

    docker_cli = shutil.which("docker")
    docker_ok, docker_output = run_command(["docker", "info"])
    image_ok, image_output = run_command(
        ["docker", "image", "inspect", image]
    )
    gpu_ok, gpu_output = run_command(
        [
            "docker",
            "run",
            "--rm",
            "--gpus",
            "all",
            "nvidia/cuda:12.1.0-base-ubuntu22.04",
            "nvidia-smi",
            "--query-gpu=name",
            "--format=csv,noheader",
        ]
    )
    carla_api = importlib.util.find_spec("carla") is not None
    display = os.environ.get("DISPLAY", "")
    x11_socket = x11_socket_path(display)
    render_mode = str(server.get("render_mode", "gui"))
    gui_ready = (
        render_mode != "gui"
        or bool(display and x11_socket is not None and x11_socket.exists())
    )
    report = {
        "config": str(config_path),
        "docker_cli": docker_cli,
        "docker_daemon_accessible": docker_ok,
        "docker_error": "" if docker_ok else docker_output[-500:],
        "carla_image": image,
        "carla_image_present": image_ok,
        "carla_image_error": "" if image_ok else image_output[-500:],
        "docker_gpu_available": gpu_ok,
        "docker_gpu": gpu_output.splitlines()[0] if gpu_ok and gpu_output else "",
        "carla_python_api": carla_api,
        "render_mode": render_mode,
        "display": display,
        "x11_socket": str(x11_socket) if x11_socket else "",
        "gui_display_ready": gui_ready,
        "rpc_endpoint": f"{host}:{port}",
        "rpc_listening": port_is_listening(host, port),
    }
    ready = all(
        (
            docker_cli,
            docker_ok,
            image_ok,
            gpu_ok,
            carla_api,
            gui_ready,
            report["rpc_listening"],
        )
    )
    return report, ready


def main() -> None:
    """命令行入口。"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="configs/carla_closed_loop.yaml",
    )
    args = parser.parse_args()
    report, ready = check_environment(Path(args.config))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not ready:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
