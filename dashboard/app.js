let allEvents = [];
let activeFilter = "all";

const colors = ["#6d2a78", "#e86f61", "#07847f", "#c99319", "#8f3d96", "#0f8a5f"];

async function getJson(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path} failed`);
  return res.json();
}

function formatCurrency(value) {
  return `₹${Math.round(value).toLocaleString("en-IN")}`;
}

function prettyName(value) {
  return String(value || "-").replaceAll("_", " ");
}

function animateNumber(el, target, formatter = (v) => Math.round(v).toString()) {
  el.textContent = formatter(target);
}

function metricCard(label, value, foot, accent, formatter) {
  return `<div class="kpi-card" style="--accent:${accent}">
    <div class="kpi-label">${label}</div>
    <div class="kpi-value" data-value="${value}" data-format="${formatter || "number"}">0</div>
    <div class="kpi-foot">${foot}</div>
  </div>`;
}

function hydrateKpis() {
  document.querySelectorAll(".kpi-value").forEach((el) => {
    const value = Number(el.dataset.value || 0);
    const format = el.dataset.format;
    const formatter =
      format === "percent"
        ? (v) => `${Math.round(v)}%`
        : format === "currency"
          ? (v) => formatCurrency(v)
          : format === "decimal"
            ? (v) => `${Number(v).toFixed(1)}m`
            : (v) => Math.round(v).toLocaleString("en-IN");
    animateNumber(el, value, formatter);
  });
}

function renderMetrics(metrics, insights) {
  document.getElementById("metrics").innerHTML = [
    metricCard("Visitors", metrics.visitors, `${metrics.active_sessions} active sessions`, colors[0]),
    metricCard("Orders", metrics.billed_orders, `${insights.transactions.rows} POS rows parsed`, colors[1]),
    metricCard("Conversion", metrics.conversion_rate * 100, "POS orders / unique visitors", colors[2], "percent"),
    metricCard("Revenue", metrics.revenue, "From Brigade_Bangalore CSV", colors[3], "currency"),
    metricCard("Avg dwell", metrics.avg_dwell_minutes, "Entry to exit session time", colors[4], "decimal"),
  ].join("");
  hydrateKpis();
  document.getElementById("confidence-score").textContent = `${Math.round(Math.min(0.97, metrics.conversion_rate + 0.08) * 100)}%`;
  document.getElementById("event-count").textContent = metrics.generated_from.events;
  document.getElementById("camera-count").textContent = insights.cameras.length;
  document.getElementById("conversion-pill").textContent = `${Math.round(metrics.conversion_rate * 100)}% conversion`;
}

function renderFunnel(funnel) {
  const first = funnel.stages[0]?.count || 1;
  document.getElementById("funnel").innerHTML = funnel.stages
    .map((stage, idx) => {
      const pct = Math.min(100, Math.round((stage.count / first) * 100));
      return `<div class="funnel-row">
        <div class="funnel-label">${prettyName(stage.name)}</div>
        <div class="funnel-track"><div class="funnel-fill" style="width:${pct}%; background:${colors[idx % colors.length]}"></div></div>
        <strong>${stage.count}</strong>
      </div>`;
    })
    .join("");
}

function renderAnomalies(anomalies) {
  document.getElementById("anomaly-count").textContent = `${anomalies.length} active`;
  document.getElementById("anomalies").innerHTML =
    anomalies.length === 0
      ? `<div class="anomaly"><strong>Clear</strong><br>No active anomaly markers.</div>`
      : anomalies
          .map((a) => `<div class="anomaly"><strong>${a.severity}</strong><br>${a.message}</div>`)
          .join("");
}

function renderCameras(cameras) {
  document.getElementById("camera-grid").innerHTML = cameras
    .map(
      (camera) => `<div class="camera-card">
        <div><strong>${camera.camera_id}</strong><span>${camera.size_mb} MB · ${camera.path}</span></div>
        <span class="camera-status" title="${camera.status}"></span>
      </div>`,
    )
    .join("");
}

function renderHourly(hourly) {
  const entries = Object.entries(hourly).map(([hour, count]) => [Number(hour), Number(count)]);
  const max = Math.max(1, ...entries.map(([, count]) => count));
  document.getElementById("hourly-bars").innerHTML = entries
    .map(([hour, count]) => `<div class="hour-row">
      <strong>${String(hour).padStart(2, "0")}:00</strong>
      <div class="hour-track"><div class="hour-fill" style="width:${Math.round((count / max) * 100)}%"></div></div>
      <span>${count}</span>
    </div>`)
    .join("");
}

function renderRanks(targetId, data) {
  document.getElementById(targetId).innerHTML = Object.entries(data)
    .slice(0, 6)
    .map(([name, count]) => `<div class="rank-item"><strong>${name}</strong><span>${count}</span></div>`)
    .join("");
}

function renderDepartmentDonut(departmentMix) {
  const entries = Object.entries(departmentMix).slice(0, 5);
  const total = entries.reduce((sum, [, count]) => sum + count, 0) || 1;
  let cursor = 0;
  const stops = entries.map(([, count], idx) => {
    const start = cursor;
    cursor += (count / total) * 100;
    return `${colors[idx % colors.length]} ${start}% ${cursor}%`;
  });
  document.getElementById("dept-donut").style.background = `conic-gradient(${stops.join(",")})`;
  renderRanks("dept-list", departmentMix);
}

function renderEvents() {
  const events = allEvents
    .filter((event) => activeFilter === "all" || event.event_type === activeFilter)
    .slice()
    .reverse()
    .slice(0, 28);
  document.getElementById("events").innerHTML = events
    .map(
      (event) => `<tr>
        <td>${new Date(event.ts).toLocaleString()}</td>
        <td><span class="event-type">${prettyName(event.event_type)}</span></td>
        <td>${event.camera_id}</td>
        <td>${event.track_id}</td>
        <td>${event.zone_id || "-"}</td>
        <td>${Math.round(event.confidence * 100)}%</td>
      </tr>`,
    )
    .join("");
}

function renderReadiness(evaluation) {
  document.getElementById("readiness").innerHTML = evaluation.acceptance_gate
    .map((item) => `<div class="ready-item"><strong>${item}</strong></div>`)
    .join("");
}

function renderResources(insights) {
  const resources = [
    ["CCTV zip", `${insights.cameras.length} extracted MP4 feeds used for detector tests`],
    ["Store layout XLSX", insights.layout.available ? "Embedded layout image extracted and displayed" : "Missing"],
    ["POS CSV", `${insights.transactions.rows} rows, ${insights.transactions.orders} unique orders`],
    ["Evaluation PDF", `${insights.evaluation.scoring.length} scoring areas mapped into readiness panel`],
  ];
  document.getElementById("resource-strip").innerHTML = resources
    .map(([name, detail]) => `<div class="resource-item"><strong>${name}</strong><span>${detail}</span></div>`)
    .join("");
}

function wireFilters() {
  document.querySelectorAll(".segmented button").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".segmented button").forEach((b) => b.classList.remove("selected"));
      button.classList.add("selected");
      activeFilter = button.dataset.filter;
      renderEvents();
    });
  });
}

async function refresh() {
  const [metrics, funnel, anomalyPayload, eventPayload, insights] = await Promise.all([
    getJson("/metrics"),
    getJson("/funnel"),
    getJson("/anomalies"),
    getJson("/events?limit=120"),
    getJson("/insights"),
  ]);

  allEvents = eventPayload.events;
  renderMetrics(metrics, insights);
  renderFunnel(funnel);
  renderAnomalies(anomalyPayload.anomalies);
  renderCameras(insights.cameras);
  renderHourly(insights.transactions.hourly_orders);
  renderDepartmentDonut(insights.transactions.department_mix);
  renderRanks("brand-list", insights.transactions.brand_mix);
  renderEvents();
  renderReadiness(insights.evaluation);
  renderResources(insights);

  const img = document.getElementById("layout-image");
  img.src = insights.layout.asset || "/dashboard/assets/store_layout.png";
}

document.getElementById("refresh").addEventListener("click", refresh);
wireFilters();
refresh();
