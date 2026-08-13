// Observability Lab Mission Control JavaScript Engine

const PRESETS = {
  custom: "",
  normal: "Chính sách hoàn tiền cho đơn hàng giao trễ là gì? Tôi cần bao lâu để nhận lại tiền?",
  pii_phone: "SĐT của tôi là 0912345678 và số phụ +84988776655, vui lòng gọi lại xác nhận hoàn tiền.",
  pii_card: "Tôi thanh toán bằng thẻ Visa 4111222233334444 và CCCD 079123456789, hãy hoàn lại tiền vào tài khoản này.",
  challenge: "I need an urgent refund for order #9821, please process it immediately through the refund system!",
  long_query: "Hãy phân tích chi tiết cách tích hợp OpenTelemetry, Prometheus và Jaeger để giám sát các hệ thống AI Agent phân tán."
};

let isLoadRunning = false;
let loadAbortController = null;
const feedHistory = [];

document.addEventListener("DOMContentLoaded", () => {
  initEventListeners();
  fetchMetrics();
  setInterval(fetchMetrics, 2500);
});

function initEventListeners() {
  // Preset selector
  const presetSelect = document.getElementById("query-preset");
  const msgInput = document.getElementById("input-message");
  const featureSelect = document.getElementById("input-feature");

  presetSelect.addEventListener("change", (e) => {
    const val = e.target.value;
    if (PRESETS[val]) {
      msgInput.value = PRESETS[val];
      if (val === "pii_card") featureSelect.value = "billing";
      else if (val === "long_query") featureSelect.value = "technical";
      else featureSelect.value = "refund";
    }
  });

  // Single Query Send
  document.getElementById("btn-send-single").addEventListener("click", handleSingleQuery);

  // Chaos Toggles
  document.querySelectorAll(".btn-toggle").forEach((btn) => {
    btn.addEventListener("click", () => {
      const incident = btn.getAttribute("data-incident");
      handleToggleIncident(incident);
    });
  });

  // Load Generator
  document.getElementById("btn-start-load").addEventListener("click", startLoadTest);
  document.getElementById("btn-stop-load").addEventListener("click", stopLoadTest);

  // Clear Feed
  document.getElementById("btn-clear-feed").addEventListener("click", () => {
    document.getElementById("feed-tbody").innerHTML = `
      <tr class="empty-row">
        <td colspan="9">Đã làm sạch bảng dữ liệu. Gửi thêm request để xem live feed!</td>
      </tr>
    `;
  });

  // Copy CID on click
  document.getElementById("res-cid").addEventListener("click", () => {
    const text = document.getElementById("res-cid").textContent.replace("cid: ", "");
    if (text && text !== "unknown") {
      navigator.clipboard.writeText(text);
      const original = document.getElementById("res-cid").textContent;
      document.getElementById("res-cid").textContent = "✓ Đã sao chép!";
      setTimeout(() => {
        document.getElementById("res-cid").textContent = original;
      }, 1500);
    }
  });
}

// Fetch live metrics from /metrics & /health
async function fetchMetrics() {
  try {
    const [resMetrics, resHealth] = await Promise.all([
      fetch("/metrics", { headers: { Accept: "application/json" } }),
      fetch("/health")
    ]);

    if (resMetrics.ok) {
      const data = await resMetrics.json();
      updateMetricCards(data);
    }

    if (resHealth.ok) {
      const health = await resHealth.json();
      updateIncidents(health.incidents || {});
    }
  } catch (err) {
    console.debug("Metrics polling error:", err);
  }
}

function updateMetricCards(data) {
  // Traffic & Error
  document.getElementById("val-traffic").innerHTML = `${data.traffic || 0} <span class="unit">reqs</span>`;
  const errRate = (data.error_rate_pct || 0).toFixed(1);
  const errFoot = document.getElementById("val-error-rate");
  errFoot.textContent = `Error Rate: ${errRate}%`;
  errFoot.style.color = data.error_rate_pct > 2.0 ? "var(--rose)" : "var(--text-dim)";

  // Latency P95
  const p95 = Math.round(data.latency_p95 || 0);
  const p95Elem = document.getElementById("val-p95");
  p95Elem.innerHTML = `${p95} <span class="unit">ms</span>`;
  p95Elem.style.color = p95 > 3000 ? "var(--rose)" : (p95 > 1500 ? "var(--amber)" : "var(--text-main)");
  document.getElementById("val-p50").textContent = `P50: ${Math.round(data.latency_p50 || 0)} ms | P99: ${Math.round(data.latency_p99 || 0)} ms`;

  // Cost & Tokens
  const cost = (data.total_cost_usd || 0).toFixed(4);
  document.getElementById("val-cost").innerHTML = `$${cost} <span class="unit">USD</span>`;
  document.getElementById("val-tokens").textContent = `In: ${data.tokens_in_total || 0} | Out: ${data.tokens_out_total || 0} tokens`;

  // Quality & SLO
  const quality = (data.quality_avg || 0).toFixed(2);
  document.getElementById("val-quality").innerHTML = `${quality} <span class="unit">/ 1.0</span>`;
  const sloElem = document.getElementById("val-slo-status");
  if (p95 > 3000 || data.error_rate_pct > 2.0) {
    sloElem.textContent = "SLO Status: BREACHED ⚠️";
    sloElem.style.color = "var(--rose)";
  } else {
    sloElem.textContent = "SLO Status: HEALTHY ✓";
    sloElem.style.color = "var(--emerald)";
  }
}

function updateIncidents(incidents) {
  let anyActive = false;
  for (const [name, active] of Object.entries(incidents)) {
    const item = document.getElementById(`item-${name}`);
    const btn = document.getElementById(`toggle-${name}`);
    if (item && btn) {
      if (active) {
        item.classList.add("active");
        btn.textContent = "ON (ACTIVE)";
        anyActive = true;
      } else {
        item.classList.remove("active");
        btn.textContent = "OFF";
      }
    }
  }

  const indicator = document.getElementById("chaos-indicator");
  if (indicator) {
    if (anyActive) {
      indicator.textContent = "Chaos Active!";
      indicator.style.color = "var(--rose)";
      indicator.style.borderColor = "var(--rose)";
      indicator.style.background = "rgba(244, 63, 94, 0.15)";
    } else {
      indicator.textContent = "System Normal";
      indicator.style.color = "var(--emerald)";
      indicator.style.borderColor = "rgba(16, 185, 129, 0.3)";
      indicator.style.background = "rgba(16, 185, 129, 0.15)";
    }
  }
}

// Toggle Incident
async function handleToggleIncident(name) {
  const item = document.getElementById(`item-${name}`);
  const isCurrentlyActive = item && item.classList.contains("active");
  const action = isCurrentlyActive ? "disable" : "enable";

  try {
    const res = await fetch(`/incidents/${name}/${action}`, { method: "POST" });
    if (res.ok) {
      const data = await res.json();
      updateIncidents(data.incidents || {});
    }
  } catch (err) {
    alert("Không thể chuyển đổi trạng thái sự cố: " + err);
  }
}

// Handle Single Query
async function handleSingleQuery() {
  const btn = document.getElementById("btn-send-single");
  const feature = document.getElementById("input-feature").value;
  const userId = document.getElementById("input-userid").value || "user_demo";
  const message = document.getElementById("input-message").value.trim();

  if (!message) {
    alert("Vui lòng nhập nội dung câu hỏi!");
    return;
  }

  btn.disabled = true;
  btn.innerHTML = `<span class="btn-icon">⏳</span> Đang gửi tới AI Agent...`;

  const startTime = performance.now();
  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: userId,
        session_id: "session_" + Date.now().toString(36),
        feature: feature,
        message: message
      })
    });

    const elapsed = Math.round(performance.now() - startTime);
    const data = await res.json();

    displaySingleResult(res.status, data, elapsed, feature);
    addFeedRow({
      timestamp: new Date().toLocaleTimeString(),
      cid: data.correlation_id || res.headers.get("x-request-id") || "err-" + Date.now(),
      feature: feature,
      status: res.status,
      latency: data.latency_ms || elapsed,
      tokensIn: data.tokens_in || 0,
      tokensOut: data.tokens_out || 0,
      cost: data.cost_usd || 0,
      quality: data.quality_score || 0
    });

    fetchMetrics();
  } catch (err) {
    displaySingleResult(500, { detail: err.message }, Math.round(performance.now() - startTime), feature);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<span class="btn-icon">⚡</span> Gửi Truy Vấn Đơn Lẻ`;
  }
}

function displaySingleResult(status, data, elapsed, feature) {
  const box = document.getElementById("single-result");
  box.classList.remove("hidden");

  const badge = document.getElementById("res-status");
  if (status === 200) {
    badge.className = "badge";
    badge.textContent = "200 OK";
    document.getElementById("res-answer").textContent = data.answer || "No response text.";
  } else {
    badge.className = "badge error";
    badge.textContent = `${status} ERROR`;
    document.getElementById("res-answer").textContent = `Error Details: ${data.detail || "Unknown error occurred"}`;
  }

  const cid = data.correlation_id || "unknown";
  document.getElementById("res-cid").textContent = `cid: ${cid}`;
  document.getElementById("res-latency").textContent = `⏱️ ${data.latency_ms || elapsed} ms`;
  document.getElementById("res-tokens").textContent = `🔤 In: ${data.tokens_in || 0} / Out: ${data.tokens_out || 0}`;
  document.getElementById("res-cost").textContent = `💵 $${(data.cost_usd || 0).toFixed(4)}`;
  document.getElementById("res-quality").textContent = `⭐ Quality: ${(data.quality_score || 0).toFixed(2)}`;
}

// Add Row to Live Feed Table
function addFeedRow(item) {
  const tbody = document.getElementById("feed-tbody");
  const emptyRow = tbody.querySelector(".empty-row");
  if (emptyRow) emptyRow.remove();

  const tr = document.createElement("tr");
  const isErr = item.status !== 200;
  const isSlow = item.latency > 2000;

  const latencyColor = isSlow ? "color: var(--rose); font-weight:700;" : (item.latency > 1000 ? "color: var(--amber);" : "");
  const statusBadge = isErr 
    ? `<span class="badge error">${item.status} FAIL</span>` 
    : `<span class="badge">200 OK</span>`;

  tr.innerHTML = `
    <td>${item.timestamp}</td>
    <td title="${item.cid}">${item.cid.slice(0, 16)}...</td>
    <td><span class="panel-tag">${item.feature}</span></td>
    <td>${statusBadge}</td>
    <td style="${latencyColor}">${item.latency} ms</td>
    <td>${item.tokensIn} / ${item.tokensOut}</td>
    <td>$${item.cost.toFixed(4)}</td>
    <td>${item.quality.toFixed(2)}</td>
    <td>
      <a href="http://localhost:16686/search?service=day13-observability-lab" target="_blank" class="link-trace" title="Mở Jaeger Tracing">
        🔍 Jaeger
      </a>
    </td>
  `;

  tbody.insertBefore(tr, tbody.firstChild);

  // Keep max 50 rows
  while (tbody.children.length > 50) {
    tbody.removeChild(tbody.lastChild);
  }
}

// Automated Load Test Runner
async function startLoadTest() {
  const total = parseInt(document.getElementById("load-count").value, 10);
  const concurrency = parseInt(document.getElementById("load-concurrency").value, 10);

  isLoadRunning = true;
  loadAbortController = new AbortController();

  document.getElementById("btn-start-load").disabled = true;
  document.getElementById("btn-stop-load").disabled = false;

  const progressWrap = document.getElementById("load-progress-wrap");
  const progressText = document.getElementById("load-progress-text");
  const progressPct = document.getElementById("load-progress-pct");
  const progressBar = document.getElementById("load-progress-bar");

  progressWrap.classList.remove("hidden");
  progressBar.style.width = "0%";

  let sent = 0;
  let completed = 0;

  const messages = [
    { feature: "refund", text: "Chính sách hoàn tiền cho sản phẩm lỗi là như thế nào?" },
    { feature: "refund", text: "Tôi muốn yêu cầu hoàn tiền nhanh đơn hàng vừa đặt." },
    { feature: "billing", text: "Chi phí gói cước hàng tháng được tính vào ngày nào?" },
    { feature: "qa", text: "Làm thế nào để liên hệ trực tiếp với tổng đài viên?" },
    { feature: "technical", text: "Hệ thống có hỗ trợ OpenTelemetry và Prometheus exporter không?" }
  ];

  async function worker() {
    while (sent < total && isLoadRunning) {
      const idx = sent++;
      const item = messages[idx % messages.length];

      try {
        const startTime = performance.now();
        const res = await fetch("/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          signal: loadAbortController.signal,
          body: JSON.stringify({
            user_id: `load_user_${idx}`,
            session_id: `load_sess_${Date.now()}`,
            feature: item.feature,
            message: item.text
          })
        });

        const elapsed = Math.round(performance.now() - startTime);
        const data = await res.json();

        addFeedRow({
          timestamp: new Date().toLocaleTimeString(),
          cid: data.correlation_id || "load-" + idx,
          feature: item.feature,
          status: res.status,
          latency: data.latency_ms || elapsed,
          tokensIn: data.tokens_in || 0,
          tokensOut: data.tokens_out || 0,
          cost: data.cost_usd || 0,
          quality: data.quality_score || 0
        });
      } catch (err) {
        if (err.name !== "AbortError") {
          addFeedRow({
            timestamp: new Date().toLocaleTimeString(),
            cid: "err-" + idx,
            feature: item.feature,
            status: 500,
            latency: 0,
            tokensIn: 0,
            tokensOut: 0,
            cost: 0,
            quality: 0
          });
        }
      } finally {
        completed++;
        const pct = Math.round((completed / total) * 100);
        progressBar.style.width = `${pct}%`;
        progressPct.textContent = `${pct}%`;
        progressText.textContent = `Đang gửi: ${completed} / ${total} requests`;
      }
    }
  }

  const workers = Array.from({ length: concurrency }, () => worker());
  await Promise.all(workers);

  stopLoadTest();
  fetchMetrics();
}

function stopLoadTest() {
  isLoadRunning = false;
  if (loadAbortController) {
    loadAbortController.abort();
  }

  document.getElementById("btn-start-load").disabled = false;
  document.getElementById("btn-stop-load").disabled = true;
}
