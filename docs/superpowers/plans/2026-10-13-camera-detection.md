# 摄像头实时检测 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 为现有火点/烟雾检测 Web 应用新增「服务端摄像头实时检测」——后端打开部署机摄像头逐帧推理，前端在第三个 tab 中实时预览并查看累计统计，可随时停止并释放设备。

**架构：** 新建独立模块 `app/routers/camera.py`（方案 B），承载摄像头采集循环与 4 个专属接口；复用现有 `tasks`（任务与停止信号）、`stats`（统计与风险）、`detector`（YOLO 推理）与 `validators.ValidationError`（统一错误格式）。不改动已验证的 `app/routers/video.py`。

**技术栈：** Python 3.12（conda `aigc`）、FastAPI、OpenCV、ultralytics、pytest、原生 HTML/CSS/JS。

**运行时解释器：** `D:\miniconda\envs\aigc\python.exe`

**规格：** `docs/superpowers/specs/2026-10-13-camera-detection-design.md`

**语言约定：** 所有面向用户的提示与页面文案使用中文。

---

## 文件结构

| 文件 | 操作 | 职责 |
|---|---|---|
| `app/config.py` | 修改 | 新增摄像头设备与帧率常量 |
| `app/tasks.py` | 修改 | `TaskRegistry` 新增 `active_of(kind)` 查询非终态任务 |
| `app/routers/camera.py` | 创建 | device 校验、采集线程 `_process_camera`、4 个接口 |
| `app/main.py` | 修改 | 挂载 camera 路由 |
| `static/index.html` | 修改 | 新增第三个 tab 与面板 |
| `static/app.js` | 修改 | 三模式切换、摄像头启停、停止隔离 |
| `tests/test_camera.py` | 创建 | device 校验、独占查询、采集循环（伪造 capture） |
| `docs/superpowers/specs/2026-10-12-fire-smoke-detection-webapp-design.md` | 修改 | 修订非目标条目、补摄像头接口与模块 |

---

## 任务 1：配置常量

**文件：**
- 修改：`app/config.py`

- [ ] **步骤 1：新增常量**

在 `app/config.py` 的 `CONF_THRESHOLD = 0.25` 之后插入：

```python
CAMERA_DEVICE_DEFAULT = 0
CAMERA_MAX_DEVICE = 9
CAMERA_TARGET_FPS = 15
```

- [ ] **步骤 2：验证可导入**

运行：`& "D:\miniconda\envs\aigc\python.exe" -c "from app import config; print(config.CAMERA_DEVICE_DEFAULT, config.CAMERA_MAX_DEVICE, config.CAMERA_TARGET_FPS)"`
预期：打印 `0 9 15`。

- [ ] **步骤 3：Commit**

```bash
git add app/config.py
git commit -m "feat: 新增摄像头设备与帧率配置常量" -m "Co-Authored-By: InspurCode"
```

---

## 任务 2：任务表新增独占查询 `active_of`（TDD）

**文件：**
- 修改：`app/tasks.py:55-72`
- 测试：`tests/test_camera.py`

- [ ] **步骤 1：编写失败的测试**

创建 `tests/test_camera.py`：

```python
import pytest

from app import tasks
from app.validators import ValidationError


def test_active_of_returns_non_terminal_task():
    reg = tasks.TaskRegistry()
    camera_task = reg.create("camera")
    camera_task.status = tasks.RUNNING
    assert reg.active_of("camera") is camera_task
    assert reg.active_of("video") is None


def test_active_of_ignores_terminal_task():
    reg = tasks.TaskRegistry()
    camera_task = reg.create("camera")
    camera_task.status = tasks.STOPPED
    assert reg.active_of("camera") is None
```

- [ ] **步骤 2：运行测试验证失败**

运行：`& "D:\miniconda\envs\aigc\python.exe" -m pytest tests/test_camera.py -v`
预期：FAIL，`AttributeError: 'TaskRegistry' object has no attribute 'active_of'`

- [ ] **步骤 3：编写实现**

在 `app/tasks.py` 的 `TaskRegistry.remove` 之前插入：

```python
    def active_of(self, kind: str):
        with self._lock:
            for task in self._tasks.values():
                if task.kind == kind and task.status not in TERMINAL:
                    return task
        return None
```

- [ ] **步骤 4：运行测试验证通过**

运行：`& "D:\miniconda\envs\aigc\python.exe" -m pytest tests/test_camera.py -v`
预期：2 passed。

- [ ] **步骤 5：Commit**

```bash
git add app/tasks.py tests/test_camera.py
git commit -m "feat: 任务表新增按类型查询非终态任务" -m "Co-Authored-By: InspurCode"
```

---

## 任务 3：设备号解析与校验（TDD）

**文件：**
- 创建：`app/routers/camera.py`
- 测试：`tests/test_camera.py`

- [ ] **步骤 1：编写失败的测试**

在 `tests/test_camera.py` 顶部 import 区补 `from app.routers import camera`，并追加：

```python
def test_parse_device_default_when_missing():
    assert camera.parse_device(None) == 0
    assert camera.parse_device("") == 0


def test_parse_device_valid_value():
    assert camera.parse_device("3") == 3
    assert camera.parse_device(str(camera.config.CAMERA_MAX_DEVICE)) == camera.config.CAMERA_MAX_DEVICE


@pytest.mark.parametrize("bad", ["-1", "10", "abc", "1.5"])
def test_parse_device_rejects_invalid(bad):
    with pytest.raises(ValidationError) as e:
        camera.parse_device(bad)
    assert "设备号" in e.value.message
```

- [ ] **步骤 2：运行测试验证失败**

运行：`& "D:\miniconda\envs\aigc\python.exe" -m pytest tests/test_camera.py -v`
预期：FAIL，`ModuleNotFoundError: No module named 'app.routers.camera'`

- [ ] **步骤 3：编写实现**

创建 `app/routers/camera.py`：

```python
from .. import config
from ..validators import ValidationError


def parse_device(raw):
    if raw is None or str(raw).strip() == "":
        return config.CAMERA_DEVICE_DEFAULT
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        raise ValidationError(
            400, f"摄像头设备号不合法，取值范围 0~{config.CAMERA_MAX_DEVICE}"
        )
    if value < 0 or value > config.CAMERA_MAX_DEVICE:
        raise ValidationError(
            400, f"摄像头设备号不合法，取值范围 0~{config.CAMERA_MAX_DEVICE}"
        )
    return value
```

- [ ] **步骤 4：运行测试验证通过**

运行：`& "D:\miniconda\envs\aigc\python.exe" -m pytest tests/test_camera.py -v`
预期：8 passed（2 + 2 + 4）。

- [ ] **步骤 5：Commit**

```bash
git add app/routers/camera.py tests/test_camera.py
git commit -m "feat: 新增摄像头设备号解析与范围校验" -m "Co-Authored-By: InspurCode"
```

---

## 任务 4：摄像头采集线程（TDD，伪造 capture）

**文件：**
- 修改：`app/routers/camera.py`
- 测试：`tests/test_camera.py`

- [ ] **步骤 1：编写失败的测试**

在 `tests/test_camera.py` 追加（顶部补 `import threading`、`import time`、`import numpy as np`）：

```python
class FakeCapture:
    def __init__(self, opened=True, frames=1000):
        self._opened = opened
        self._frames = frames
        self.released = False

    def isOpened(self):
        return self._opened

    def read(self):
        if self._frames <= 0:
            return False, None
        self._frames -= 1
        return True, np.zeros((8, 8, 3), dtype=np.uint8)

    def release(self):
        self.released = True


class FakeDetector:
    def infer(self, frame):
        return frame, [], 0


def test_process_camera_open_failure(monkeypatch):
    monkeypatch.setattr(camera.cv2, "VideoCapture", lambda d: FakeCapture(opened=False))
    task = tasks.Task("camera")
    camera._process_camera(task, 0, FakeDetector())
    assert task.status == tasks.ERROR
    assert task.error == camera.CAMERA_ERROR_OPEN


def test_process_camera_read_failure(monkeypatch):
    monkeypatch.setattr(camera.cv2, "VideoCapture", lambda d: FakeCapture(opened=True, frames=0))
    task = tasks.Task("camera")
    camera._process_camera(task, 0, FakeDetector())
    assert task.status == tasks.ERROR
    assert task.error == camera.CAMERA_ERROR_READ


def test_process_camera_collects_frames_then_releases(monkeypatch):
    fake = FakeCapture(opened=True, frames=1000)
    monkeypatch.setattr(camera.cv2, "VideoCapture", lambda d: fake)
    task = tasks.Task("camera")
    thread = threading.Thread(target=camera._process_camera, args=(task, 0, FakeDetector()))
    thread.start()
    for _ in range(300):
        if task.stats.frames >= 3:
            break
        time.sleep(0.01)
    task.request_stop()
    thread.join(timeout=5)
    assert task.status == tasks.STOPPED
    assert task.stats.frames >= 3
    assert task.latest_jpeg is not None
    assert fake.released is True
```

- [ ] **步骤 2：运行测试验证失败**

运行：`& "D:\miniconda\envs\aigc\python.exe" -m pytest tests/test_camera.py -v`
预期：FAIL，`AttributeError: module 'app.routers.camera' has no attribute '_process_camera'`

- [ ] **步骤 3：编写实现**

把 `app/routers/camera.py` 顶部的 import 块（任务 3 写入的 `from .. import config` 与 `from ..validators import ValidationError` 两行）**整体替换**为：

```python
import threading

import cv2

from .. import config, tasks
from ..validators import ValidationError

CAMERA_ERROR_OPEN = "无法打开摄像头，请确认设备存在且未被占用"
CAMERA_ERROR_READ = "摄像头画面读取失败，设备可能已断开"
```

然后在 `parse_device` 函数之后追加 `_process_camera`：

```python
def _process_camera(task, device, detector):
    cap = cv2.VideoCapture(device)
    try:
        if not cap.isOpened():
            task.status = tasks.ERROR
            task.error = CAMERA_ERROR_OPEN
            return
        task.status = tasks.RUNNING
        delay = 1.0 / config.CAMERA_TARGET_FPS
        while not task.stop_event.is_set():
            ok, frame = cap.read()
            if not ok:
                task.status = tasks.ERROR
                task.error = CAMERA_ERROR_READ
                return
            annotated, detections, _ = detector.infer(frame)
            task.stats.accumulate(detections)
            ok, buf = cv2.imencode(".jpg", annotated)
            if ok:
                task.set_frame(buf.tobytes())
            if task.stop_event.wait(delay):
                break
        task.status = tasks.STOPPED
    except Exception:  # noqa: BLE001
        task.status = tasks.ERROR
        task.error = "摄像头处理中断，请重试"
    finally:
        cap.release()
```

> 注意：`parse_device` 已在任务 3 中定义，本次只在文件内追加 `_process_camera` 与常量，不重复定义。

- [ ] **步骤 4：运行测试验证通过**

运行：`& "D:\miniconda\envs\aigc\python.exe" -m pytest tests/test_camera.py -v`
预期：11 passed，且无真实摄像头依赖。

- [ ] **步骤 5：Commit**

```bash
git add app/routers/camera.py tests/test_camera.py
git commit -m "feat: 新增摄像头采集与推理循环" -m "Co-Authored-By: InspurCode"
```

---

## 任务 5：摄像头四个接口

**文件：**
- 修改：`app/routers/camera.py`

- [ ] **步骤 1：替换 import 块**

把 `app/routers/camera.py` 顶部的 import 块**整体替换**为（在任务 4 的基础上新增 `asyncio` 与 `fastapi`）：

```python
import asyncio
import threading

import cv2
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from .. import config, tasks
from ..validators import ValidationError

router = APIRouter()

CAMERA_ERROR_OPEN = "无法打开摄像头，请确认设备存在且未被占用"
CAMERA_ERROR_READ = "摄像头画面读取失败，设备可能已断开"

_BOUNDARY = "frame"
```

- [ ] **步骤 2：追加 `_mime_chunk` 与四个接口实现**

在文件末尾追加：

```python
def _mime_chunk(jpeg: bytes) -> bytes:
    return (
        b"--" + _BOUNDARY.encode() + b"\r\n"
        b"Content-Type: image/jpeg\r\n"
        b"Content-Length: " + str(len(jpeg)).encode() + b"\r\n\r\n" + jpeg + b"\r\n"
    )


@router.post("/api/detect/camera/start")
async def start_camera(request: Request, device: str = Query(default=None)):
    parsed = parse_device(device)
    registry = request.app.state.registry
    if registry.active_of("camera") is not None:
        raise HTTPException(
            status_code=409,
            detail={"code": 409, "message": "摄像头正在使用中，请先停止当前摄像头任务"},
        )
    task = registry.create("camera")
    task.source_name = f"摄像头 {parsed}"
    thread = threading.Thread(
        target=_process_camera,
        args=(task, parsed, request.app.state.detector),
        daemon=True,
    )
    thread.start()
    return {"task_id": task.id}


@router.get("/api/detect/camera/status/{task_id}")
async def camera_status(request: Request, task_id: str):
    task = request.app.state.registry.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "任务不存在或已结束"})
    return task.status_payload()


@router.post("/api/detect/camera/stop/{task_id}")
async def camera_stop(request: Request, task_id: str):
    task = request.app.state.registry.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "任务不存在或已结束"})
    task.request_stop()
    return {"task_id": task_id, "status": task.status}


@router.get("/api/detect/camera/stream/{task_id}")
async def camera_stream(request: Request, task_id: str):
    task = request.app.state.registry.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "任务不存在或已结束"})

    async def generator():
        while True:
            with task.frame_lock:
                jpeg = task.latest_jpeg
            if jpeg is not None:
                yield _mime_chunk(jpeg)
            if task.status in tasks.TERMINAL:
                break
            await asyncio.sleep(0.03)
        yield b"--" + _BOUNDARY.encode() + b"--\r\n"

    return StreamingResponse(
        generator(), media_type=f"multipart/x-mixed-replace; boundary={_BOUNDARY}"
    )
```

- [ ] **步骤 3：冒烟验证模块可导入**

运行：`& "D:\miniconda\envs\aigc\python.exe" -c "from app.routers import camera; print([r.path for r in camera.router.routes])"`
预期：打印包含 4 个 `/api/detect/camera/...` 路径的列表。

- [ ] **步骤 4：Commit**

```bash
git add app/routers/camera.py
git commit -m "feat: 新增摄像头启停/状态/流接口" -m "Co-Authored-By: InspurCode"
```

---

## 任务 6：挂载路由并验证接口可用

**文件：**
- 修改：`app/main.py`

- [ ] **步骤 1：挂载路由**

在 `app/main.py` 中把：

```python
from .routers import image, video
```

改为：

```python
from .routers import camera, image, video
```

并在：

```python
app.include_router(image.router)
app.include_router(video.router)
```

之后追加：

```python
app.include_router(camera.router)
```

- [ ] **步骤 2：启动服务验证接口存在**

运行：`& "D:\miniconda\envs\aigc\python.exe" -m uvicorn app.main:app --port 8000`
预期：启动无异常；访问 `http://localhost:8000/docs` 可见 `/api/detect/camera/start` 等 4 个接口。

- [ ] **步骤 3：验证 device 非法返回 400**

运行：`Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/detect/camera/start?device=abc"`
预期：返回 400，body 为 `{"code":400,"message":"摄像头设备号不合法，取值范围 0~9"}`。

- [ ] **步骤 4：Commit**

```bash
git add app/main.py
git commit -m "feat: 挂载摄像头检测路由" -m "Co-Authored-By: InspurCode"
```

---

## 任务 7：前端第三 tab 与面板

**文件：**
- 修改：`static/index.html`

- [ ] **步骤 1：新增 tab 按钮**

把：

```html
  <button id="tab-video" class="tab" data-mode="video">视频检测</button>
```

改为：

```html
  <button id="tab-video" class="tab" data-mode="video">视频检测</button>
  <button id="tab-camera" class="tab" data-mode="camera">摄像头检测</button>
```

- [ ] **步骤 2：新增摄像头面板**

在 `</section>`（视频面板结束）之后、`<div id="message"` 之前插入：

```html
  <section id="panel-camera" class="panel hidden">
    <label for="camera-device">设备号</label>
    <input type="number" id="camera-device" value="0" min="0" max="9" style="width:80px" />
    <button id="camera-start">开启摄像头</button>
    <button id="camera-stop" disabled>关闭摄像头</button>
    <span id="camera-status" class="badge">未开启</span>
  </section>
```

- [ ] **步骤 3：Commit**

```bash
git add static/index.html
git commit -m "feat: 前端新增摄像头检测页签与面板" -m "Co-Authored-By: InspurCode"
```

---

## 任务 8：前端三模式切换与摄像头启停

**文件：**
- 修改：`static/app.js`

- [ ] **步骤 1：扩展模式切换**

把 `switchMode` 函数体：

```javascript
function switchMode(next) {
  mode = next;
  document.querySelectorAll(".tab").forEach((t) =>
    t.classList.toggle("active", t.dataset.mode === next)
  );
  $("panel-image").classList.toggle("hidden", next !== "image");
  $("panel-video").classList.toggle("hidden", next !== "video");
  if (next !== "video") stopVideoTask();
  $("preview").src = "";
  resetStats();
  showMessage("");
}
```

替换为：

```javascript
function switchMode(next) {
  mode = next;
  document.querySelectorAll(".tab").forEach((t) =>
    t.classList.toggle("active", t.dataset.mode === next)
  );
  $("panel-image").classList.toggle("hidden", next !== "image");
  $("panel-video").classList.toggle("hidden", next !== "video");
  $("panel-camera").classList.toggle("hidden", next !== "camera");
  if (next !== "video") stopVideoTask();
  if (next !== "camera") stopCameraTask();
  $("preview").src = "";
  resetStats();
  showMessage("");
}
```

- [ ] **步骤 2：新增摄像头启停逻辑**

在 `document.querySelectorAll(".tab").forEach(...)` 之前追加：

```javascript
$("camera-start").onclick = async () => {
  const device = ($("camera-device").value || "0").trim();
  showMessage("");
  stopCameraTask();
  try {
    const resp = await fetch(
      `/api/detect/camera/start?device=${encodeURIComponent(device)}`,
      { method: "POST" }
    );
    if (!resp.ok) { showMessage(await parseError(resp)); return; }
    const data = await resp.json();
    currentTaskId = data.task_id;
    $("preview").src = `/api/detect/camera/stream/${currentTaskId}`;
    $("camera-stop").disabled = false;
    $("camera-start").disabled = true;
    $("camera-status").textContent = "检测中";
    pollTimer = setInterval(() => pollStatus(currentTaskId), 600);
  } catch (e) {
    showMessage("网络异常，请重试");
  }
};

$("camera-stop").onclick = () => stopCameraTask();

async function stopCameraTask() {
  if (!currentTaskId) return;
  const id = currentTaskId;
  currentTaskId = null;
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
  $("camera-stop").disabled = true;
  $("camera-start").disabled = false;
  $("camera-status").textContent = "已关闭";
  try { await fetch(`/api/detect/camera/stop/${id}`, { method: "POST" }); } catch (e) {}
}
```

- [ ] **步骤 3：让轮询复位摄像头按钮**

把 `pollStatus` 中的终止分支：

```javascript
    if (["done", "stopped", "error"].includes(s.status)) {
      if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
      $("video-stop").disabled = true;
      if (id === currentTaskId) currentTaskId = null;
    }
```

替换为：

```javascript
    if (["done", "stopped", "error"].includes(s.status)) {
      if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
      $("video-stop").disabled = true;
      $("camera-stop").disabled = true;
      $("camera-start").disabled = false;
      if (id === currentTaskId) currentTaskId = null;
    }
```

- [ ] **步骤 4：浏览器验证**

启动服务后打开 http://localhost:8000 ，切到「摄像头检测」：
- 无摄像头时点「开启摄像头」→ 状态徽标先「检测中」后「处理失败」，页面提示「无法打开摄像头，请确认设备存在且未被占用」。
- 切到「图片检测」→ 摄像头任务自动停止。

- [ ] **步骤 5：Commit**

```bash
git add static/app.js
git commit -m "feat: 前端支持摄像头模式启停与模式隔离" -m "Co-Authored-By: InspurCode"
```

---

## 任务 9：修订原设计文档

**文件：**
- 修改：`docs/superpowers/specs/2026-10-12-fire-smoke-detection-webapp-design.md`

- [ ] **步骤 1：修订非目标条目**

把：

```
- 不做真实视频流（RTSP/摄像头）接入。
```

改为：

```
- 不做真实视频流（RTSP）接入。
- 摄像头实时检测为后续新增能力，见 `2026-10-13-camera-detection-design.md`。
```

- [ ] **步骤 2：补充模块与接口**

在本文件第 4 节目录结构的 `routers/` 列表中，把：

```
│     └─ video.py       # POST /api/detect/video, GET /stream/{id}, POST /stop/{id}, GET /status/{id}
```

改为：

```
│     ├─ video.py       # POST /api/detect/video, GET /stream/{id}, POST /stop/{id}, GET /status/{id}
│     └─ camera.py      # POST /api/detect/camera/start, GET /status/{id}, POST /stop/{id}, GET /stream/{id}
```

- [ ] **步骤 3：Commit**

```bash
git add docs/superpowers/specs/2026-10-12-fire-smoke-detection-webapp-design.md
git commit -m "docs: 修订原设计文档的摄像头能力与非目标" -m "Co-Authored-By: InspurCode"
```

---

## 任务 10：端到端与回归验证

**文件：** 无（验证任务）

- [ ] **步骤 1：运行全部单元测试**

运行：`& "D:\miniconda\envs\aigc\python.exe" -m pytest -q`
预期：原有 15 passed + 新增 11 passed = 26 passed。

- [ ] **步骤 2：回归图片与视频接口**

运行既有端到端脚本（或手工）验证：图片检测返回 200 与标注图；视频任务可创建、完成、停止。
预期：行为与新增摄像头功能前一致（未改动 `video.py`）。

- [ ] **步骤 3：摄像头端到端验证（需部署机有摄像头）**

- 正向：输入设备号 0 → 点「开启摄像头」→ 预览实时刷新、状态「检测中」、统计滚动更新。
- 停止：点「关闭摄像头」→ 状态「已停止」，统计保留，随后重新开启可再次成功（验证设备已释放）。
- 独占：摄像头运行中再点「开启摄像头」（另一标签页）→ 返回 409 提示。
- 隔离：摄像头运行中切到「视频检测」→ 摄像头任务自动停止。
- 失败：设备号填 9（通常不存在）→ 提示「无法打开摄像头，请确认设备存在且未被占用」。

- [ ] **步骤 4：无摄像头环境的替代验证**

若部署机无摄像头，用伪造验证覆盖：`pytest tests/test_camera.py -v` 全绿即证明打开失败、读取失败、正常停止与释放三条路径均正确。

- [ ] **步骤 5：Commit（如验证过程产生修复）**

```bash
git add -A
git commit -m "test: 完成摄像头检测端到端验证" -m "Co-Authored-By: InspurCode"
```

---

## 需求覆盖对照

| 规格条目 | 覆盖任务 |
|---|---|
| 4 个接口 | 任务 5、6 |
| device 校验（400） | 任务 3 |
| 摄像头独占（409） | 任务 2、5 |
| 采集循环与释放 | 任务 4 |
| 配置常量 | 任务 1 |
| 前端第三 tab | 任务 7、8 |
| 修订原设计文档 | 任务 9 |
| 测试与验证 | 任务 2、3、4、10 |

## 安全覆盖对照

| 规则 | 覆盖 |
|---|---|
| SEC-03/13 输入校验与资源上限 | 任务 3（device 范围）、任务 2（单摄像头独占） |
| SEC-04 输出最小化 | 任务 4（固定错误文案，不含路径）、任务 5（返回固定字段） |
| SEC-01 鉴权豁免 | 沿用本地单机工具的显式豁免（见设计文档 7.2） |
