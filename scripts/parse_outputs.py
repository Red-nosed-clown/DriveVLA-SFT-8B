#!/usr/bin/env python3
"""解析 DriveVLA 模型输出，并把结果保存为结构化 JSONL。

解析顺序：
1. 直接使用 json.loads。
2. 去掉 Markdown 代码块后再次解析。
3. 从混合文本中提取第一个完整 JSON 对象。
4. 使用正则表达式兼容旧版 Action/Risk/Trajectory/Reason 文本。

这样设计的原因是生成模型偶尔会添加解释或代码块。评估脚本不能因为一条
输出格式不完美就中断整个验证集。
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
from typing import Any


VALID_ACTIONS = {
    "KEEP_LANE",
    "TURN_LEFT",
    "TURN_RIGHT",
    "SLOW_DOWN",
    "STOP",
    "LANE_CHANGE_LEFT",
    "LANE_CHANGE_RIGHT",
}
VALID_RISKS = {"LOW", "MEDIUM", "HIGH"}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """读取 JSONL。

    输入：
        path：预测结果文件。

    输出：
        每行 JSON 对象组成的列表。

    为什么这样做：
        逐行解析时可以准确报告损坏行的位置，便于排查推理中断问题。
    """
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path} 第 {line_number} 行不是合法 JSON：{exc}") from exc
    return rows


def save_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    """把结构化结果逐行写入 JSONL。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def remove_code_fence(text: str) -> str:
    """去掉模型常见的 Markdown JSON 代码块标记。"""
    stripped = text.strip()
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", stripped, flags=re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else stripped


def extract_first_json_object(text: str) -> str | None:
    """使用括号深度提取第一个完整 JSON 对象。

    输入：
        text：可能包含额外解释的模型输出。

    输出：
        找到时返回 JSON 子串，否则返回 None。

    为什么这样做：
        简单的贪婪正则在字符串包含花括号时容易截错，括号深度更稳定。
    """
    start = text.find("{")
    if start < 0:
        return None

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def normalize_trajectory(value: Any) -> list[list[float]] | None:
    """检查轨迹是否为六个有限二维坐标点。"""
    if not isinstance(value, list) or len(value) != 6:
        return None
    trajectory: list[list[float]] = []
    for point in value:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            return None
        try:
            forward = float(point[0])
            lateral = float(point[1])
        except (TypeError, ValueError):
            return None
        if not (-1e6 < forward < 1e6 and -1e6 < lateral < 1e6):
            return None
        trajectory.append([forward, lateral])
    return trajectory


def normalize_result(data: Any, parser_name: str) -> dict[str, Any]:
    """统一字段名并验证 Action、Risk 和六点轨迹。"""
    if not isinstance(data, dict):
        data = {}
    lowered = {str(key).lower(): value for key, value in data.items()}
    action = str(lowered.get("action", "UNKNOWN")).strip().upper()
    risk = str(lowered.get("risk", "UNKNOWN")).strip().upper()
    trajectory = normalize_trajectory(lowered.get("trajectory"))
    reason = str(lowered.get("reason", "")).strip()
    target_speed = None
    try:
        candidate_speed = float(lowered.get("target_speed_mps"))
        if 0.0 <= candidate_speed < 100.0:
            target_speed = candidate_speed
    except (TypeError, ValueError):
        pass

    action_valid = action in VALID_ACTIONS
    risk_valid = risk in VALID_RISKS
    trajectory_valid = trajectory is not None
    return {
        "parse_success": action_valid and risk_valid and trajectory_valid,
        "parser": parser_name,
        "action": action if action_valid else "UNKNOWN",
        "risk": risk if risk_valid else "UNKNOWN",
        "trajectory": trajectory,
        "reason": reason,
        "target_speed_mps": target_speed,
        "action_valid": action_valid,
        "risk_valid": risk_valid,
        "trajectory_valid": trajectory_valid,
    }


def parse_legacy_text(text: str) -> dict[str, Any]:
    """使用正则兼容旧版四行文本输出。"""
    action_match = re.search(r"Action\s*:\s*([A-Z_]+)", text, flags=re.IGNORECASE)
    risk_match = re.search(r"Risk\s*:\s*([A-Z_]+)", text, flags=re.IGNORECASE)
    trajectory_match = re.search(r"Trajectory\s*:\s*(\[\s*\[.*?\]\s*\])", text, flags=re.DOTALL | re.IGNORECASE)
    reason_match = re.search(r"Reason\s*:\s*(.*)", text, flags=re.DOTALL | re.IGNORECASE)

    trajectory: Any = None
    if trajectory_match:
        try:
            trajectory = ast.literal_eval(trajectory_match.group(1))
        except (SyntaxError, ValueError):
            trajectory = None
    return {
        "action": action_match.group(1) if action_match else "UNKNOWN",
        "risk": risk_match.group(1) if risk_match else "UNKNOWN",
        "trajectory": trajectory,
        "reason": reason_match.group(1).strip() if reason_match else "",
    }


def parse_model_output(text: str) -> dict[str, Any]:
    """按多级策略解析一条模型输出。

    输入：
        text：模型生成的原始字符串。

    输出：
        统一字段的解析结果，并记录实际采用的解析器。

    为什么保留“部分成功”的候选：
        模型可能正确输出 Action 和 Risk，但轨迹只有 5 个点。此时整条结果的
        parse_success 仍应为 False，不过 Action/Risk 仍可用于各自的准确率。
        如果直接丢弃这个 JSON 再走正则兜底，会把已经正确的字段也变成 UNKNOWN。
    """
    candidates = [
        ("json", text.strip()),
        ("code_fence", remove_code_fence(text)),
    ]
    extracted = extract_first_json_object(text)
    if extracted:
        candidates.append(("extracted_json", extracted))

    attempted: set[str] = set()
    parsed_candidates: list[dict[str, Any]] = []
    for parser_name, candidate in candidates:
        if not candidate or candidate in attempted:
            continue
        attempted.add(candidate)
        try:
            result = normalize_result(json.loads(candidate), parser_name)
            if result["parse_success"]:
                return result
            parsed_candidates.append(result)
        except json.JSONDecodeError:
            continue

    legacy_result = normalize_result(parse_legacy_text(text), "legacy_regex")
    if legacy_result["parse_success"]:
        return legacy_result
    parsed_candidates.append(legacy_result)

    # 优先保留有效字段最多的候选。Python 的 max 在分数相同时保留最先出现的
    # 项，因此严格 JSON 会自然优先于后面的正则兜底。
    return max(
        parsed_candidates,
        key=lambda result: sum(
            bool(result[field])
            for field in ("action_valid", "risk_valid", "trajectory_valid")
        ),
    )


def parse_file(args: argparse.Namespace) -> None:
    """解析整个预测文件，并保留原始字段用于后续评估。"""
    input_path = Path(args.input_path)
    output_path = Path(args.output_path)
    parsed_rows: list[dict[str, Any]] = []
    for row in load_jsonl(input_path):
        parsed_row = dict(row)
        parsed_row["parsed_prediction"] = parse_model_output(str(row.get("prediction", "")))
        parsed_rows.append(parsed_row)
    save_jsonl(output_path, parsed_rows)
    success_count = sum(row["parsed_prediction"]["parse_success"] for row in parsed_rows)
    print(f"解析完成：{success_count}/{len(parsed_rows)} 条成功")
    print(f"输出文件：{output_path}")


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-path", required=True)
    parser.add_argument("--output-path", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    parse_file(parse_args())
