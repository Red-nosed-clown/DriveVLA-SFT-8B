# CARLA 闭环接入

## 当前架构

闭环链路拆成四层，避免把模型推理、控制器和模拟器耦合在一个脚本里：

1. CARLA RGB 相机提供当前前视图像和 ego speed；
2. Qwen3-VL 输出 `action/risk/trajectory/reason`；
3. `WaypointController` 把六点轨迹转换成 `steer/throttle/brake`；
4. 安全层在解析失败、预测超时或轨迹越界时执行紧急制动。

第一阶段固定使用 `CARLA 0.9.16`、`Town10HD_Opt`、20 Hz 同步模式和 Docker GUI
服务端。模型不直接输出油门与方向盘，这样可以继续复用 nuScenes 训练得到的六点
轨迹，并将模型误差与低层控制误差分开分析。

第一版使用 CARLA actor 真值构造场景统计，目的是先验证规划与控制闭环；该输入
属于 privileged simulator state，报告中必须明确标注。后续再替换为纯视觉检测器。

## 环境准备

拉取官方服务端镜像：

```bash
docker pull carlasim/carla:0.9.16
```

在 `drivevla_sft` 安装相同版本的 Python API：

```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  /home/pc/miniconda3/envs/drivevla_sft/bin/python \
  -m pip install carla==0.9.16
```

默认启动 1280×720 有界面服务端：

```bash
bash scripts/run_carla_server.sh
```

闭环客户端必须在 CARLA 服务端启动并显示地图后运行。推荐使用两个终端：第一个
终端始终运行服务端，第二个终端运行 `run_carla_closed_loop.py`。默认配置会把
GUI 观察者固定在 ego 后上方；距离、高度和俯角可在 `spectator` 配置中调整。

提高窗口分辨率但保持 Low 画质（真 Qwen 同卡运行时推荐）：

```bash
CARLA_WINDOW_WIDTH=1600 CARLA_WINDOW_HEIGHT=900 \
  CARLA_QUALITY_LEVEL=Low bash scripts/run_carla_server.sh
```

只录制演示或使用 mock 规划器时可以启用 Epic 画质：

```bash
CARLA_WINDOW_WIDTH=1920 CARLA_WINDOW_HEIGHT=1080 \
  CARLA_QUALITY_LEVEL=Epic bash scripts/run_carla_server.sh
```

Epic 会明显增加 CARLA Vulkan 显存占用。它不适合当前 Qwen 与 CARLA 共用单卡的
正式长测；模型输入清晰度由 `camera.width/height` 和
`planner.image_max_pixels` 单独控制，不等同于 GUI 窗口清晰度。

首次启动前可确认当前桌面终端存在 `DISPLAY`：

```bash
echo "$DISPLAY"
ls -l /tmp/.X11-unix
```

需要批量跑指标时切换为无界面模式：

```bash
CARLA_RENDER_MODE=headless bash scripts/run_carla_server.sh
```

另开终端运行连接测试：

```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  /home/pc/miniconda3/envs/drivevla_sft/bin/python \
  scripts/carla_smoke_client.py
```

环境汇总检查：

```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  /home/pc/miniconda3/envs/drivevla_sft/bin/python \
  scripts/check_carla_environment.py
```

## 安全约束

- 模型轨迹必须恰好包含 6 个有限二维点；
- 轨迹年龄从相机采集时刻开始计算，超过 5 秒未更新时立即制动；
- 控制循环不会同步等待 VLM，后台始终只处理最新一帧；
- 横向位移、相邻点跳变和明显倒退轨迹都会触发制动；
- DriveVLA lateral 正值是左，CARLA steer 正值是右，控制器显式取反；
- STOP 将目标速度设为 0，SLOW_DOWN 将目标速度限制为 4 m/s。

## 第一阶段验收

- Docker 服务端能够在 RTX 5090 上显示 CARLA 窗口；
- 客户端与服务端 API 版本均为 0.9.16；
- 同步模式连续运行 200 tick，不发生客户端超时；
- 直行、左右转和停止轨迹的控制方向正确；
- 所有安全异常都能稳定触发紧急制动。

完成基础连接后再接入 Qwen 推理，并统计路线完成率、碰撞、越界、安全接管率、
推理 p50/p95 延迟和控制频率。

## 闭环短测

先用 mock 规划器验证相机、控制器和日志，不加载 8B 模型：

```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  /home/pc/miniconda3/envs/drivevla_sft/bin/python \
  scripts/run_carla_closed_loop.py --mock-planner --max-steps 40 \
  --output results/carla/mock_smoke_40.jsonl
```

mock 通过后运行本地 v5 Qwen3-VL 模型：

```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false \
  /home/pc/miniconda3/envs/drivevla_sft/bin/python \
  scripts/run_carla_closed_loop.py --max-steps 200 \
  --output results/carla/qwen_episode_200.jsonl
```

逐帧 JSONL 包含模型解析结果、轨迹年龄、车辆速度、控制量、接管原因和累计碰撞；
同目录的 `*_summary.json` 汇总位移、碰撞、安全接管率与推理延迟。

## NPC 路线基准

默认配置会沿 ego 出生车道构造 50 米目标路线，并生成 15 辆 Traffic Manager
车辆。路线进度使用“最近车道点 + 累计行驶距离上界”计算，防止立交或回环道路的
空间重叠导致完成率虚高。额外记录以下字段：

- `route_completion`：已完成路线比例；
- `distance_to_goal_m`：当前位置到路线终点的三维距离；
- `traveled_distance_m`：车辆实际累计里程；
- `collisions` 和 `lane_invasions`：碰撞与车道线侵入事件数；
- `fallback_reasons`：启动等待、轨迹超时和格式错误等安全接管原因。

2026-08-03 的工程短测结果如下。这些结果只验证链路，不作为正式模型结论：

| Planner | Steps | NPC | Route completion | Collision | Lane invasion | P50 latency |
|---|---:|---:|---:|---:|---:|---:|
| Mock | 40 | 15 | 12.00% | 0 | 0 | 0.00 s |
| Qwen3-VL v5 | 100 | 15 | 4.00% | 0 | 0 | 3.22 s |

Qwen 与 CARLA GUI 共用 RTX 5090 时，未限制 PyTorch 显存曾导致 CARLA Vulkan
报 `VK_ERROR_OUT_OF_DEVICE_MEMORY`。当前配置会先初始化 CARLA 相机缓冲，再将
PyTorch 进程限制为 55%，并在每次生成后释放缓存；模型加载期间积累的旧相机帧
也会被丢弃。真模型短测结束后 CARLA 保持运行，空闲显存占用约 5.3 GB。
正式报告必须使用多 seed、相同路线和相同交通配置重复评测。

## 路口场景与双频 fallback

配置中的 `scenario.route_command` 支持 `STRAIGHT`、`LEFT` 和 `RIGHT`。启用
`require_junction` 后，ego 只会从前方指定距离内存在 junction 的出生点中按 seed
选择。命令行可覆盖场景和随机种子：

```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false \
  /home/pc/miniconda3/envs/drivevla_sft/bin/python \
  scripts/run_carla_closed_loop.py --route-command LEFT --seed 42 \
  --max-steps 400 --output results/carla/qwen_intersection_left_400.jsonl
```

Qwen 推理超过 5 秒轨迹时限时，系统不再立即满刹，而是使用 CARLA 车道中心线
构造六点局部轨迹并限制到 `SLOW_DOWN` 速度。该控制明确记录为
`route_fallback_timeout`，属于 privileged simulator fallback，不能计为纯 VLA
规划成功。解析失败和非法轨迹仍执行紧急制动。

2026-08-03 的 LEFT/seed=42/15 NPC 真模型短测结果：

- 路线完成率 95.83%，到达终点；
- 0 碰撞、0 车道侵入；
- fallback rate 41.75%，hard-brake rate 20.50%；
- 平均推理延迟 2.86 秒，P95 3.31 秒；
- 动作分布包含 `KEEP_LANE=3`、`STOP=1`、`TURN_RIGHT=1`、`SLOW_DOWN=1`。

模型在 LEFT 指令下仍出现 `TURN_RIGHT`，说明当前路口成功含有 fallback 的贡献，
不能据此宣称模型已掌握左转。后续正式评测应同时报告纯 VLA 控制占比、fallback
占比和指令一致率。

## 能力对齐场景

当前模型未使用导航命令条件训练，因此正式能力评测使用以下场景，不要求模型服从
LEFT/RIGHT 指令：

| 场景 | 主要能力 | 期望动作 |
|---|---|---|
| `empty_straight` | 空旷道路稳定性 | KEEP_LANE |
| `natural_curve` | 从视觉和历史运动预测自然弯道 | KEEP_LANE/TURN |
| `lead_slow` | 跟随慢速前车 | SLOW_DOWN |
| `lead_stop` | 静止障碍停车 | STOP/SLOW_DOWN |
| `dense_traffic` | 多车环境风险与动作稳定性 | KEEP_LANE/SLOW_DOWN/STOP |

例如运行静止前车场景：

```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false \
  PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  /home/pc/miniconda3/envs/drivevla_sft/bin/python \
  scripts/run_carla_closed_loop.py --scenario-name lead_stop --seed 42 \
  --max-steps 300 --output results/carla/qwen_lead_stop_seed42.jsonl
```

`lead_stop` 和 `lead_slow` 会在 ego 同车道前方约 18 米生成受控车辆，并记录
`minimum_lead_distance_m`、`stopped_for_lead`、`collision_occurred` 和
`safe_stop_success`。安全停车要求车辆停止、没有碰撞且最小中心距离不小于 5 米。

2026-08-03 的 `lead_stop/seed=42` 真模型结果：模型 5 次预测中输出
`KEEP_LANE=3、STOP=2`，但最小距离为 4.46 米并发生碰撞，安全停车失败；平均推理
延迟 2.81 秒。这说明模型具有部分停车语义，但当前延迟和动作稳定性不足以保证
闭环安全。碰撞回调数不是碰撞次数，同一次持续接触会产生多个回调；正式汇总优先
使用布尔字段 `collision_occurred`。

## 多 Seed 批量评测

批量器在同一 Python 进程内复用一次 Qwen 权重，默认运行五类能力场景与五个 seed；
已有 summary 会自动跳过，中断后可重复执行同一命令续跑：

```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false \
  PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  /home/pc/miniconda3/envs/drivevla_sft/bin/python \
  scripts/run_carla_capability_batch.py \
  --seeds 7 21 42 84 123 --max-steps 300 \
  --results-dir results/carla/generalization
```

完成后查看：

```bash
cat results/carla/generalization/capability_generalization_summary.md
```

需要覆盖已有结果时显式增加 `--overwrite`。批量开始前必须先启动 CARLA；若服务端
中途退出，重新启动 CARLA 后再次执行原命令即可从未完成组合继续。
