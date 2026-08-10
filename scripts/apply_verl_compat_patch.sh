#!/usr/bin/env bash
set -euo pipefail

# VERL_DIR 可指向任意本地 VERL 源码目录，默认使用本机教学环境中的 editable clone。
VERL_DIR="${VERL_DIR:-/tmp/verl-drivevla-reference}"
PATCH_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/patches/verl_qwen3vl_fsdp2_compat.patch"

if git -C "${VERL_DIR}" apply --reverse --check "${PATCH_FILE}" >/dev/null 2>&1; then
  echo "VERL 兼容补丁已经应用，无需重复执行。"
  exit 0
fi

git -C "${VERL_DIR}" apply --check "${PATCH_FILE}"
git -C "${VERL_DIR}" apply "${PATCH_FILE}"
echo "已应用 Qwen3-VL + FSDP2 + LoRA 单卡兼容补丁。"
