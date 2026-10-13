# AGENTS.md（luzhibei）

## 设计文档规范（强制）

编辑或新增 `docs/superpowers/specs/` 下的设计文档时，**必须包含 Mermaid 图**，不接受纯文字：

- **系统架构图**：组件分层与调用关系（`graph TB`）。
- **数据流图**：每条业务流一张（`sequenceDiagram`），含异步 / 线程 / 流式路径。
- **信任边界图**：安全章节内（`graph LR`），标注不可信边界、内部信任域、跨边界校验点与数据敏感等级（L1~L4）。
- **模型调用链**：外部依赖的调用路径（`graph LR`）。

要求：
- 使用 Mermaid 围栏代码块。
- 节点标注**实际文件与函数位置**（如 `app/detector.py:33`），图与代码保持一致。
- 参考样例：`docs/superpowers/specs/2026-10-12-fire-smoke-detection-webapp-design.md`（5.1~5.4 架构与数据流、9.1 信任边界）。

## 项目速览

- 运行时：`D:\miniconda\envs\aigc\python.exe`（Python 3.12）
- 启动：`& "D:\miniconda\envs\aigc\python.exe" -m uvicorn app.main:app --port 8000`
- 测试：`& "D:\miniconda\envs\aigc\python.exe" -m pytest -q`
- 占位权重 `models/yolov8n.pt`（COCO 80 类，不含 fire/smoke）；真实权重到位后改 `app/config.py` 的 `MODEL_PATH` 并复验 `FIRE_LABELS`/`SMOKE_LABELS`。

## UI 实现参考

前端按全局「监控大屏风格」规范实现（规范细节见 `ui-monitoring-dashboard.md`，本项目的实现示例）：

- `static/index.html`、`static/style.css`、`static/app.js`
- 设计说明：`docs/superpowers/specs/2026-10-13-monitoring-dashboard-redesign.md`
