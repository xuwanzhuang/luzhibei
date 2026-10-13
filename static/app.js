const $ = (id) => document.getElementById(id);
let mode = "image";
let currentTaskId = null;
let pollTimer = null;

function showMessage(text) {
  const el = $("message");
  if (!text) { el.classList.add("hidden"); el.textContent = ""; return; }
  el.textContent = text;
  el.classList.remove("hidden");
}

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

function resetStats() {
  $("risk").className = "risk normal";
  $("risk").textContent = "风险等级：正常";
  $("summary").textContent = "";
  $("detections").querySelector("tbody").innerHTML = "";
}

function renderRisk(risk) {
  const text = { normal: "正常", medium: "中风险", high: "高风险" }[risk] || risk;
  $("risk").className = "risk " + risk;
  $("risk").textContent = "风险等级：" + text;
}

function renderDetections(list) {
  const tbody = $("detections").querySelector("tbody");
  tbody.innerHTML = "";
  list.forEach((d) => {
    const tr = document.createElement("tr");
    const loc = d.bbox.map((v) => Math.round(v)).join(",");
    [`${d.label}(${d.category})`, d.confidence.toFixed(2), loc].forEach((v) => {
      const td = document.createElement("td");
      td.textContent = v;
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
}

async function parseError(resp) {
  try {
    const data = await resp.json();
    const msg = data.message || (data.detail && data.detail.message) || "请求失败";
    return msg;
  } catch (e) {
    return "请求失败（" + resp.status + "）";
  }
}

$("image-start").onclick = async () => {
  const file = $("image-input").files[0];
  if (!file) { showMessage("请选择要检测的图片"); return; }
  showMessage("");
  const fd = new FormData();
  fd.append("file", file);
  try {
    const resp = await fetch("/api/detect/image", { method: "POST", body: fd });
    if (!resp.ok) { showMessage(await parseError(resp)); return; }
    const data = await resp.json();
    $("preview").src = data.image;
    renderRisk(data.stats.risk);
    const c = data.stats.counts;
    $("summary").textContent =
      `火点：${c.fire}　烟雾：${c.smoke}　其它：${c.other}　合计：${c.total}　耗时：${data.elapsed_ms}ms　时间：${data.detected_at}`;
    renderDetections(data.detections);
  } catch (e) {
    showMessage("网络异常，请重试");
  }
};

$("video-start").onclick = async () => {
  const file = $("video-input").files[0];
  if (!file) { showMessage("请选择要检测的视频"); return; }
  showMessage("");
  stopVideoTask();
  const fd = new FormData();
  fd.append("file", file);
  try {
    const resp = await fetch("/api/detect/video", { method: "POST", body: fd });
    if (!resp.ok) { showMessage(await parseError(resp)); return; }
    const data = await resp.json();
    currentTaskId = data.task_id;
    $("preview").src = `/api/detect/video/stream/${currentTaskId}`;
    $("video-stop").disabled = false;
    $("video-status").textContent = "检测中";
    pollTimer = setInterval(() => pollStatus(currentTaskId), 600);
  } catch (e) {
    showMessage("网络异常，请重试");
  }
};

$("video-stop").onclick = () => stopVideoTask();

async function stopVideoTask() {
  if (!currentTaskId) return;
  const id = currentTaskId;
  currentTaskId = null;
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
  $("video-stop").disabled = true;
  try { await fetch(`/api/detect/video/stop/${id}`, { method: "POST" }); } catch (e) {}
}

async function pollStatus(id) {
  try {
    const resp = await fetch(`/api/detect/video/status/${id}`);
    if (!resp.ok) return;
    const s = await resp.json();
    if (id !== currentTaskId) return;  // 旧任务结果不得覆盖新任务
    $("video-status").textContent = s.status_text;
    renderRisk(s.stats.risk);
    const c = s.stats.total;
    const p = s.stats.peak;
    $("summary").textContent =
      `已处理帧：${s.stats.frames}　火点累计：${c.fire}（峰值${p.fire}）　烟雾累计：${c.smoke}（峰值${p.smoke}）　其它：${c.other}`;
    if (s.error) showMessage(s.error);
    if (["done", "stopped", "error"].includes(s.status)) {
      if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
      $("video-stop").disabled = true;
      $("camera-stop").disabled = true;
      $("camera-start").disabled = false;
      if (id === currentTaskId) currentTaskId = null;
    }
  } catch (e) {}
}

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

document.querySelectorAll(".tab").forEach((t) => {
  t.onclick = () => switchMode(t.dataset.mode);
});
