#!/usr/bin/env python3
"""检查 DriveVLA QLoRA 训练所需的软件和 GPU 环境。

这个脚本不会修改环境，只会读取版本和硬件状态。初学者可以先运行它，
确认问题出在环境还是项目代码，避免训练到一半才发现 CUDA 或依赖不可用。
"""

from __future__ import annotations

import importlib
import os
import platform
import sys
from pathlib import Path
from typing import Any


REQUIRED_MODULES = (
    "torch",
    "transformers",
    "peft",
    "bitsandbytes",
    "qwen_vl_utils",
    "yaml",
)


def import_module(name: str) -> tuple[bool, Any | None, str]:
    """尝试导入一个 Python 模块。

    输入：
        name：模块名，例如 ``torch`` 或 ``transformers``。

    输出：
        三元组 ``(是否成功, 模块对象, 错误信息)``。

    为什么这样做：
        把导入异常转换为普通返回值后，脚本可以继续检查其他依赖，一次性
        展示完整报告，而不是在第一个缺失包处直接退出。
    """
    try:
        module = importlib.import_module(name)
        return True, module, ""
    except Exception as exc:  # 环境检查需要完整展示导入失败原因。
        return False, None, f"{type(exc).__name__}: {exc}"


def main() -> int:
    """执行全部环境检查并返回进程状态码。

    输入：
        无。信息来自当前 Python 解释器、环境变量和 PyTorch。

    输出：
        全部关键检查通过时返回 0，否则返回 1。

    为什么这样做：
        Shell 和持续集成工具都能根据状态码判断检查是否通过，同时人也能
        从终端输出中看到具体版本和失败原因。
    """
    print("=== DriveVLA 环境检查 ===")
    print(f"Python: {platform.python_version()}")
    print(f"Executable: {sys.executable}")
    # 直接调用某个 Conda 环境里的 python 时，CONDA_DEFAULT_ENV 可能仍是
    # 外层终端的旧值。sys.prefix 才是当前解释器真正所属的环境目录。
    actual_env = Path(sys.prefix).name
    declared_env = os.environ.get("CONDA_DEFAULT_ENV", "未激活")
    print(f"Conda env (Python prefix): {actual_env}")
    print(f"Conda env (shell variable): {declared_env}")

    pythonpath = os.environ.get("PYTHONPATH", "")
    if "isaac_sim" in pythonpath or "orbit" in pythonpath:
        print("WARNING: PYTHONPATH 包含 Isaac Sim/Orbit 路径，建议训练命令前执行 unset PYTHONPATH。")

    failed = False
    imported: dict[str, Any] = {}
    for module_name in REQUIRED_MODULES:
        ok, module, error = import_module(module_name)
        if ok:
            version = getattr(module, "__version__", "unknown")
            print(f"[OK] {module_name}: {version}")
            imported[module_name] = module
        else:
            print(f"[FAIL] {module_name}: {error}")
            failed = True

    torch = imported.get("torch")
    if torch is None:
        return 1

    print(f"PyTorch CUDA build: {torch.version.cuda}")
    if not torch.cuda.is_available():
        print("[FAIL] CUDA 不可用，请先确认驱动、容器权限和 CUDA 版 PyTorch。")
        return 1

    device = torch.cuda.get_device_properties(0)
    print(f"GPU: {device.name}")
    print(f"VRAM: {device.total_memory / 1024**3:.2f} GiB")
    print(f"Compute capability: {device.major}.{device.minor}")
    print(f"BF16 supported: {torch.cuda.is_bf16_supported()}")

    try:
        from transformers import Qwen3VLForConditionalGeneration  # noqa: F401

        print("[OK] Qwen3VLForConditionalGeneration 可导入")
    except Exception as exc:
        print(f"[FAIL] Qwen3VLForConditionalGeneration: {type(exc).__name__}: {exc}")
        failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
