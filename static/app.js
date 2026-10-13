const $ = (id) => document.getElementById(id);

let mode = "image";
let currentTaskId = null;
let activeKind = null;
let pollTimer = null;
let lastAlertKey = "";
let soundOn = false;
let audioCtx = null;

const TREND_MAX = 60;
const ALERT_LOG_MAX = 50;
const trendData = [];

const PLACEHOLDER_TEXT = {
  image: "请选择图片并点击「开始检测」",
  video: "请选择视频并点击「开始检测」",
  camera: "请点击「开启摄像头」开始实时检测",
};
const MODE_TEXT = { image: "图片检测", video: "视频检测", camera: "摄像头检测" };
const RISK_TEXT = { normal: "正常", medium: "中风险", high: "高风险" };
const ALERT_TEXT = { alarm: "报警", warn: "预警" };

function showMessage(text) {
  const el = $("message");
  if (!text) { el.classList.add("hidden"); el.textContent = ""; return; }
  el.textContent = text;
  el.classList.remove("hidden");
}

function showPlaceholder(text) {
  $("placeholder").textContent = text;
  $("placeholder").classList.remove("hidden");
  $("preview").classList.add("hidden");
  $("preview").removeAttribute("src");
}

function showPreview(src) {
  $("preview").src = src;
  $("preview").classList.remove("hidden");
  $("placeholder").classList.add("hidden");
}

function updateClock() {
  $("clock").textContent = new Date().toLocaleTimeString("zh-CN", { hour12: false });
}

function nowText() {
  return new Date().toLocaleTimeString("zh-CN", { hour12: false });
}

function renderStats(stats, extra) {
  if (!stats) return;
  const cumulative = !!stats.total;
  const live = stats.current || stats;
  const liveCounts = live.counts || {};

  $("kpi-total").textContent = liveCounts.total || 0;
  $("kpi-fire").textContent = liveCounts.fire || 0;
  $("kpi-smoke").textContent = liveCounts.smoke || 0;

  const risk = live.risk || "normal";
  const riskEl = $("kpi-risk");
  riskEl.textContent = RISK_TEXT[risk] || risk;
  riskEl.className = "kpi-value risk-" + risk;

  if (cumulative) {
    $("meta-frames").textContent = stats.frames || 0;
    $("meta-total").textContent = (stats.total && stats.total.total) || 0;
    pushTrend(liveCounts.total || 0);
  } else if (extra && extra.elapsed_ms != null) {
    $("meta-elapsed").textContent = extra.elapsed_ms + " ms";
  }
  $("meta-time").textContent = (extra && extra.detected_at) || nowText();

  renderLabels(live.by_label || {}, cumulative ? stats.peak : null);
  applyAlerts(live.alerts || []);
}

function renderLabels(byLabel, peak) {
  const entries = Object.entries(byLabel).filter(([, n]) => n > 0);
  const box = $("labels");
  box.innerHTML = "";
  if (!entries.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "暂无检测数据";
    box.appendChild(empty);
    return;
  }
  entries.sort((a, b) => b[1] - a[1]);
  const max = entries[0][1];
  entries.slice(0, 8).forEach(([label, n]) => {
    const row = document.createElement("div");
    row.className = "label-row";

    const name = document.createElement("span");
    name.textContent = label;

    const val = document.createElement("b");
    val.textContent = peak && peak[label] ? `${n}（峰值${peak[label]}）` : String(n);

    const bar = document.createElement("div");
    bar.className = "label-bar";
    const fill = document.createElement("span");
    fill.style.width = Math.max(6, Math.round((n / max) * 100)) + "%";
    bar.appendChild(fill);

    row.appendChild(name);
    row.appendChild(val);
    row.appendChild(bar);
    box.appendChild(row);
  });
}

function pushTrend(value) {
  trendData.push(value);
  while (trendData.length > TREND_MAX) trendData.shift();
  drawTrend();
}

function drawTrend() {
  const canvas = $("trend");
  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);

  ctx.strokeStyle = "rgba(148,163,184,.18)";
  ctx.lineWidth = 1;
  for (let i = 1; i < 4; i++) {
    const y = (h / 4) * i;
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(w, y);
    ctx.stroke();
  }

  if (trendData.length < 2) return;
  const max = Math.max(1, ...trendData);
  const step = w / (TREND_MAX - 1);
  const points = trendData.map((v, i) => [i * step, h - (v / max) * (h - 14) - 7]);

  ctx.beginPath();
  points.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
  ctx.strokeStyle = "#22d3ee";
  ctx.lineWidth = 2;
  ctx.stroke();

  const grad = ctx.createLinearGradient(0, 0, 0, h);
  grad.addColorStop(0, "rgba(34,211,238,.35)");
  grad.addColorStop(1, "rgba(34,211,238,0)");
  ctx.lineTo(points[points.length - 1][0], h);
  ctx.lineTo(points[0][0], h);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();
}

function applyAlerts(alerts) {
  const hasAlarm = alerts.some((a) => a.level === "alarm");
  const hasWarn = alerts.some((a) => a.level === "warn");
  const lampClass = hasAlarm ? "alarm" : hasWarn ? "warn" : "ok";

  $("lamp").className = "lamp " + lampClass;
  $("lamp-text").textContent = hasAlarm ? "报警" : hasWarn ? "预警" : "系统正常";
  document.body.classList.toggle("alarm", hasAlarm);
  document.body.classList.toggle("warn", !hasAlarm && hasWarn);

  const key = alerts.map((a) => a.label + ":" + a.level).sort().join(",");
  if (key && key !== lastAlertKey) {
    const level = hasAlarm ? "alarm" : "warn";
    appendAlert(alerts.map((a) => a.label).join(" / "), level);
    beep(level);
  }
  lastAlertKey = key;
}

function appendAlert(text, level) {
  const box = $("alert-log");
  const empty = box.querySelector(".alert-empty");
  if (empty) empty.remove();

  const row = document.createElement("div");
  row.className = "alert-item " + level;

  const time = document.createElement("span");
  time.className = "alert-time";
  time.textContent = nowText();

  const tag = document.createElement("b");
  tag.textContent = ALERT_TEXT[level] || level;

  const msg = document.createElement("span");
  msg.textContent = "检测到 " + text;

  row.appendChild(time);
  row.appendChild(tag);
  row.appendChild(msg);
  box.prepend(row);

  while (box.children.length > ALERT_LOG_MAX) box.removeChild(box.lastChild);
}

function beep(level) {
  if (!soundOn) return;
  try {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
    const offsets = level === "alarm" ? [0, 0.24] : [0];
    offsets.forEach((offset) => {
      const t0 = audioCtx.currentTime + offset;
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = "square";
      osc.frequency.value = level === "alarm" ? 880 : 660;
      gain.gain.setValueAtTime(0.0001, t0);
      gain.gain.exponentialRampToValueAtTime(0.15, t0 + 0.01);
      gain.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.18);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start(t0);
      osc.stop(t0 + 0.2);
    });
  } catch (e) {}
}

function resetStats() {
  trendData.length = 0;
  drawTrend();
  lastAlertKey = "";

  $("kpi-total").textContent = "0";
  $("kpi-fire").textContent = "0";
  $("kpi-smoke").textContent = "0";
  $("kpi-risk").textContent = "正常";
  $("kpi-risk").className = "kpi-value risk-normal";
  $("meta-frames").textContent = "0";
  $("meta-total").textContent = "0";
  $("meta-elapsed").textContent = "-";
  $("meta-time").textContent = "-";

  renderLabels({}, null);

  $("lamp").className = "lamp ok";
  $("lamp-text").textContent = "系统正常";
  document.body.classList.remove("alarm", "warn");
}

function switchMode(next) {
  mode = next;
  document.querySelectorAll(".tab").forEach((t) =>
    t.classList.toggle("active", t.dataset.mode === next)
  );
  $("mode-chip").textContent = MODE_TEXT[next] || next;
  $("panel-image").classList.toggle("hidden", next !== "image");
  $("panel-video").classList.toggle("hidden", next !== "video");
  $("panel-camera").classList.toggle("hidden", next !== "camera");
  stopActiveTask();
  showPlaceholder(PLACEHOLDER_TEXT[next] || "");
  resetStats();
  showMessage("");
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
}

async function parseError(resp) {
  try {
    const data = await resp.json();
    return data.message || (data.detail && data.detail.message) || "请求失败";
  } catch (e) {
    return "请求失败（" + resp.status + "）";
  }
}

async function stopActiveTask() {
  if (!currentTaskId) return;
  const kind = activeKind;
  const id = currentTaskId;
  currentTaskId = null;
  activeKind = null;
  stopPolling();

  if (kind === "video") {
    $("video-stop").disabled = true;
    $("video-status").textContent = "已停止";
  } else if (kind === "camera") {
    $("camera-stop").disabled = true;
    $("camera-start").disabled = false;
    $("camera-status").textContent = "已关闭";
  }
  if (kind) {
    try { await fetch(`/api/detect/${kind}/stop/${id}`, { method: "POST" }); } catch (e) {}
  }
}

async function startStreamTask(kind, prepare) {
  stopActiveTask();
  try {
    const taskId = await prepare();
    if (!taskId) return;
    currentTaskId = taskId;
    activeKind = kind;
    showPreview(`/api/detect/${kind}/stream/${taskId}`);
    stopPolling();
    pollTimer = setInterval(() => pollStatus(taskId, kind), 600);
  } catch (e) {
    showMessage("网络异常，请重试");
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
    showPreview(data.image);
    renderStats(data.stats, data);
  } catch (e) {
    showMessage("网络异常，请重试");
  }
};

$("video-start").onclick = () => {
  const file = $("video-input").files[0];
  if (!file) { showMessage("请选择要检测的视频"); return; }
  showMessage("");
  const fd = new FormData();
  fd.append("file", file);
  startStreamTask("video", async () => {
    const resp = await fetch("/api/detect/video", { method: "POST", body: fd });
    if (!resp.ok) { showMessage(await parseError(resp)); return null; }
    const data = await resp.json();
    $("video-stop").disabled = false;
    $("video-status").textContent = "检测中";
    return data.task_id;
  });
};

$("camera-start").onclick = () => {
  const device = ($("camera-device").value || "0").trim();
  showMessage("");
  startStreamTask("camera", async () => {
    const resp = await fetch(
      `/api/detect/camera/start?device=${encodeURIComponent(device)}`,
      { method: "POST" }
    );
    if (!resp.ok) { showMessage(await parseError(resp)); return null; }
    const data = await resp.json();
    $("camera-stop").disabled = false;
    $("camera-start").disabled = true;
    $("camera-status").textContent = "检测中";
    return data.task_id;
  });
};

$("video-stop").onclick = () => stopActiveTask();
$("camera-stop").onclick = () => stopActiveTask();

async function pollStatus(id, kind) {
  try {
    const resp = await fetch(`/api/detect/${kind}/status/${id}`);
    if (!resp.ok) return;
    const s = await resp.json();
    if (id !== currentTaskId) return;  // 旧任务结果不得覆盖新任务
    $(kind === "camera" ? "camera-status" : "video-status").textContent = s.status_text;
    renderStats(s.stats, { detected_at: nowText() });
    if (s.error) showMessage(s.error);
    if (["done", "stopped", "error"].includes(s.status)) {
      stopPolling();
      activeKind = null;
      $("video-stop").disabled = true;
      $("camera-stop").disabled = true;
      $("camera-start").disabled = false;
      if (id === currentTaskId) currentTaskId = null;
    }
  } catch (e) {}
}

$("sound-toggle").onclick = () => {
  soundOn = !soundOn;
  $("sound-toggle").textContent = soundOn ? "提示音：开启" : "提示音：关闭";
};

document.querySelectorAll(".tab").forEach((t) => {
  t.onclick = () => switchMode(t.dataset.mode);
});

setInterval(updateClock, 1000);
updateClock();
drawTrend();
