#!/usr/bin/env bash
set -euo pipefail

# CARLA 服务端固定使用 0.9.16，Python API 也必须保持相同版本。
IMAGE="${CARLA_IMAGE:-carlasim/carla:0.9.16}"
RPC_PORT="${CARLA_RPC_PORT:-2000}"
CONTAINER_NAME="${CARLA_CONTAINER_NAME:-drivevla-carla-0916}"
RENDER_MODE="${CARLA_RENDER_MODE:-gui}"
QUALITY_LEVEL="${CARLA_QUALITY_LEVEL:-Low}"
WINDOW_WIDTH="${CARLA_WINDOW_WIDTH:-1280}"
WINDOW_HEIGHT="${CARLA_WINDOW_HEIGHT:-720}"
MAP="${CARLA_MAP:-Town10HD_Opt}"

COMMON_ARGS=(
  --rm
  --name "${CONTAINER_NAME}"
  --gpus all
  --net=host
  --env NVIDIA_VISIBLE_DEVICES=all
  --env NVIDIA_DRIVER_CAPABILITIES=all
)

# 某些新版 nvidia-container-toolkit 会挂载 NVIDIA 图形库，却遗漏 Vulkan ICD
# 描述文件。缺少它时 CARLA 会退回 CPU 的 lavapipe，窗口和 RPC 都可能卡死。
NVIDIA_VULKAN_ICD="/usr/share/vulkan/icd.d/nvidia_icd.json"
if [[ -f "${NVIDIA_VULKAN_ICD}" ]]; then
  COMMON_ARGS+=(
    --volume "${NVIDIA_VULKAN_ICD}:${NVIDIA_VULKAN_ICD}:ro"
    --env VK_ICD_FILENAMES="${NVIDIA_VULKAN_ICD}"
  )
else
  echo "警告：未找到 ${NVIDIA_VULKAN_ICD}，CARLA 可能退回软件 Vulkan。"
fi

CARLA_ARGS=(
  "/Game/Carla/Maps/${MAP}"
  -nosound
  -carla-rpc-port="${RPC_PORT}"
  -quality-level="${QUALITY_LEVEL}"
)

if [[ "${RENDER_MODE}" == "gui" ]]; then
  if [[ -z "${DISPLAY:-}" ]]; then
    echo "错误：GUI 模式缺少 DISPLAY，请在桌面终端中运行。"
    exit 1
  fi
  if [[ ! -d /tmp/.X11-unix ]]; then
    echo "错误：找不到 /tmp/.X11-unix，无法显示 CARLA 窗口。"
    exit 1
  fi

  # 容器使用当前桌面用户身份，从而复用 X11 的本地用户授权。
  COMMON_ARGS+=(
    --user "$(id -u):$(id -g)"
    --env DISPLAY="${DISPLAY}"
    --volume /tmp/.X11-unix:/tmp/.X11-unix:rw
  )
  CARLA_ARGS+=(
    -windowed
    -ResX="${WINDOW_WIDTH}"
    -ResY="${WINDOW_HEIGHT}"
  )
elif [[ "${RENDER_MODE}" == "headless" ]]; then
  CARLA_ARGS+=(-RenderOffScreen)
else
  echo "错误：CARLA_RENDER_MODE 只能是 gui 或 headless。"
  exit 1
fi

echo "启动 CARLA ${RENDER_MODE} 模式：${IMAGE}，RPC 端口 ${RPC_PORT}"
docker run "${COMMON_ARGS[@]}" \
  "${IMAGE}" \
  bash CarlaUE4.sh "${CARLA_ARGS[@]}"
