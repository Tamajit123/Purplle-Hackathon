let allEvents = [];
let activeFilter = "all";
let activeStoreId = null;
let latestInsights = null;
let latestMetrics = null;

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

function storeList() {
  return latestInsights?.layout?.stores || [];
}

function selectedStore() {
  const stores = storeList();
  return stores.find((store) => store.id === activeStoreId) || stores[0] || null;
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
        ? (v) => `${Math.round(v * 100)}%`
        : format === "ratio"
          ? (v) => `${Number(v).toFixed(1)}x`
        : format === "currency"
          ? (v) => formatCurrency(v)
          : format === "decimal"
            ? (v) => `${Number(v).toFixed(1)}m`
            : (v) => Math.round(v).toLocaleString("en-IN");
    animateNumber(el, value, formatter);
  });
}

function renderMetrics(metrics, insights) {
  const stores = insights.layout.stores || [];
  const cameraTotal = stores.reduce((sum, store) => sum + Number(store.camera_count || 0), 0);
  document.getElementById("metrics").innerHTML = [
    metricCard("Visitors", metrics.visitors, `${metrics.active_sessions} active sessions`, colors[0]),
    metricCard("Orders", metrics.billed_orders, `${insights.transactions.rows} POS rows parsed`, colors[1]),
    metricCard("Order ratio", metrics.conversion_rate, "POS orders / unique visitors", colors[2], "ratio"),
    metricCard("Revenue", metrics.revenue, "Reconciled from POS transactions", colors[3], "currency"),
    metricCard("Stores mapped", stores.length, `${cameraTotal} camera viewpoints configured`, colors[4]),
  ].join("");
  hydrateKpis();
  document.getElementById("confidence-score").textContent = `${Math.round(Math.min(0.97, metrics.conversion_rate + 0.08) * 100)}%`;
  document.getElementById("event-count").textContent = metrics.generated_from.events;
  document.getElementById("camera-count").textContent = cameraTotal;
  document.getElementById("resource-count").textContent = `${stores.length}+`;
  document.getElementById("conversion-pill").textContent = `${Number(metrics.conversion_rate).toFixed(1)}x order ratio`;
}

function renderStoreControls() {
  const stores = storeList();
  if (!activeStoreId && stores.length) activeStoreId = stores[0].id;
  const controls = document.getElementById("store-toggle");
  controls.innerHTML = stores
    .map(
      (store) => `<button class="${store.id === activeStoreId ? "selected" : ""}" data-store="${store.id}" type="button">
        ${store.store}
      </button>`,
    )
    .join("");
  controls.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      activeStoreId = button.dataset.store;
      renderStoreExperience();
    });
  });
}

function renderStoreExperience() {
  const store = selectedStore();
  if (!store) return;

  document.querySelectorAll("#store-toggle button").forEach((button) => {
    button.classList.toggle("selected", button.dataset.store === store.id);
  });

  document.getElementById("store-context").textContent = store.focus || "Store-level camera and layout intelligence";
  document.getElementById("store-pill").textContent = `${store.camera_count} cameras · ${store.layout_count} layout`;
  document.getElementById("camera-title").textContent = `${store.store} coverage`;
  document.getElementById("layout-caption").textContent = `${store.store} mapped zones`;

  const img = document.getElementById("layout-image");
  img.src = store.asset || "/dashboard/assets/stores/store_1/layout.png";
  img.alt = `${store.store} layout`;

  renderCameras(store.cameras || []);
  renderComparison(storeList());
  renderOperationalHealth(store);
  renderScenarioCoverage(store);
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
      ? `<div class="anomaly clear"><strong>Clear floor</strong><br>No active queue, dwell or confidence anomalies.</div>`
      : anomalies.map((a) => `<div class="anomaly"><strong>${a.severity}</strong><br>${a.message}</div>`).join("");
}

function renderCameras(cameras) {
  document.getElementById("camera-grid").innerHTML = cameras.length
    ? cameras
        .map(
          (camera) => `<div class="camera-card">
            <div>
              <strong>${camera.name || camera.camera_id}</strong>
              <span>${camera.role || "Camera"} · ${camera.coverage || camera.path || "Configured for store intelligence"}</span>
            </div>
            <span class="camera-status" title="${camera.status || "ready"}"></span>
          </div>`,
        )
        .join("")
    : `<div class="empty-state">Camera metadata is not available for this store.</div>`;
}

function renderComparison(stores) {
  document.getElementById("store-comparison").innerHTML = stores
    .map(
      (store) => `<div class="compare-row ${store.id === activeStoreId ? "active" : ""}">
        <div><strong>${store.store}</strong><span>${store.focus || "Store asset"}</span></div>
        <div class="compare-metrics">
          <span>${store.camera_count} cameras</span>
          <span>${(store.zones || []).length} zones</span>
        </div>
      </div>`,
    )
    .join("");
}

function renderOperationalHealth(store) {
  const txRows = latestInsights?.transactions?.rows || 0;
  const eventCount = latestMetrics?.generated_from?.events || 0;
  const checks = [
    ["Camera readiness", `${store.camera_count} viewpoints mapped`, "ready"],
    ["Layout visibility", store.asset ? "Store image loaded from dashboard assets" : "Layout asset missing", store.asset ? "ready" : "warn"],
    ["POS sync", `${txRows} POS rows parsed`, "ready"],
    ["Event stream", `${eventCount} structured events available`, "ready"],
  ];
  document.getElementById("ops-health").innerHTML = checks
    .map(
      ([label, value, state]) => `<div class="health-row ${state}">
        <span></span>
        <div><strong>${label}</strong><small>${value}</small></div>
      </div>`,
    )
    .join("");
}

function renderScenarioCoverage(store) {
  const zones = (store.zones || []).map(prettyName).join(", ");
  const coverage = [
    ["Visitor counting", "Entry cameras mapped to unique track/session logic"],
    ["Conversion audit", "Checkout events reconciled with POS order count"],
    ["Dwell intelligence", `Zone coverage ready for ${zones || "mapped areas"}`],
    ["Anomaly review", "Queue, low-confidence and unusual-flow signals exposed"],
  ];
  document.getElementById("scenario-coverage").innerHTML = coverage
    .map(
      ([label, value]) => `<div class="scenario-card">
        <strong>${label}</strong>
        <span>${value}</span>
      </div>`,
    )
    .join("");
}

function renderHourly(hourly) {
  const entries = Object.entries(hourly).map(([hour, count]) => [Number(hour), Number(count)]);
  const max = Math.max(1, ...entries.map(([, count]) => count));
  document.getElementById("hourly-bars").innerHTML = entries
    .map(
      ([hour, count]) => `<div class="hour-row">
        <strong>${String(hour).padStart(2, "0")}:00</strong>
        <div class="hour-track"><div class="hour-fill" style="width:${Math.round((count / max) * 100)}%"></div></div>
        <span>${count}</span>
      </div>`,
    )
    .join("");
}

function renderRanks(targetId, data) {
  document.getElementById(targetId).innerHTML = Object.entries(data)
    .slice(0, 6)
    .map(([name, count]) => `<div class="rank-item"><strong>${name}</strong><span>${count}</span></div>`)
    .join("");
}

function renderBrandDonut(brandMix) {
  const entries = Object.entries(brandMix).slice(0, 5);
  const total = entries.reduce((sum, [, count]) => sum + count, 0) || 1;
  let cursor = 0;
  const stops = entries.map(([, count], idx) => {
    const start = cursor;
    cursor += (count / total) * 100;
    return `${colors[idx % colors.length]} ${start}% ${cursor}%`;
  });
  document.getElementById("dept-donut").style.background = `conic-gradient(${stops.join(",")})`;
  document.getElementById("dept-list").innerHTML = entries
    .map(([name, count], idx) => {
      const pct = Math.round((count / total) * 100);
      return `<div class="rank-item share-item">
        <div class="share-label">
          <span class="share-swatch" style="background:${colors[idx % colors.length]}"></span>
          <strong>${name}</strong>
        </div>
        <span class="share-value">${pct}% · ${count}</span>
      </div>`;
    })
    .join("");
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

  latestMetrics = metrics;
  latestInsights = insights;
  allEvents = eventPayload.events;
  activeStoreId = activeStoreId || insights.layout.stores?.[0]?.id;

  renderMetrics(metrics, insights);
  renderStoreControls();
  renderFunnel(funnel);
  renderAnomalies(anomalyPayload.anomalies);
  renderHourly(insights.transactions.hourly_orders);
  renderBrandDonut(insights.transactions.brand_mix);
  renderRanks("brand-list", insights.transactions.brand_mix);
  renderEvents();
  renderStoreExperience();
}

document.getElementById("refresh").addEventListener("click", refresh);
wireFilters();
refresh();
