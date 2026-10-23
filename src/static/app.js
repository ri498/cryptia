// State
let selectedCrypto = "BTC";
let activeTab = "train";
let horizonDays = 7;
let cryptos = [];
let historyChart = null;
let forecastChart = null;
let currentHistoryData = [];

// Initialize
document.addEventListener("DOMContentLoaded", async () => {
  if (window.lucide) lucide.createIcons();
  await loadCryptos();
  await loadCryptoData();
});

// Toast Helper
function showToast(message, type = "info") {
  const toast = document.getElementById("toast");
  const msg = document.getElementById("toast-message");
  const icon = document.getElementById("toast-icon");

  msg.textContent = message;
  toast.className = "p-4 rounded-xl border flex items-center justify-between shadow-2xl transition-all";

  if (type === "success") {
    toast.classList.add("bg-emerald-950/80", "border-emerald-600", "text-emerald-200");
  } else if (type === "error") {
    toast.classList.add("bg-rose-950/80", "border-rose-600", "text-rose-200");
  } else {
    toast.classList.add("bg-sky-950/80", "border-sky-600", "text-sky-200");
  }

  toast.classList.remove("hidden");
  if (window.lucide) lucide.createIcons();

  setTimeout(() => {
    hideToast();
  }, 5000);
}

function hideToast() {
  document.getElementById("toast").classList.add("hidden");
}

// Tab Switching
function switchTab(tab) {
  activeTab = tab;
  const trainBtn = document.getElementById("tab-train-btn");
  const predictBtn = document.getElementById("tab-predict-btn");
  const trainView = document.getElementById("train-view");
  const predictView = document.getElementById("predict-view");

  if (tab === "train") {
    trainBtn.className = "flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium transition-all bg-brand-600 text-white shadow-md";
    predictBtn.className = "flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium transition-all text-slate-400 hover:text-white hover:bg-dark-700";
    trainView.classList.remove("hidden");
    predictView.classList.add("hidden");
  } else {
    predictBtn.className = "flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium transition-all bg-brand-600 text-white shadow-md";
    trainBtn.className = "flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium transition-all text-slate-400 hover:text-white hover:bg-dark-700";
    predictView.classList.remove("hidden");
    trainView.classList.add("hidden");
  }
}

// Load List of Cryptos
async function loadCryptos() {
  try {
    const res = await fetch("/api/cryptos");
    const data = await res.json();
    cryptos = data.cryptos;
    renderCryptoCards();
  } catch (err) {
    console.error("Failed to load cryptos:", err);
    showToast("Failed to connect to API backend.", "error");
  }
}

// Render Crypto Selection Strip
function renderCryptoCards() {
  const container = document.getElementById("crypto-cards-container");
  container.innerHTML = "";

  cryptos.forEach((c) => {
    const isSelected = c.symbol === selectedCrypto;
    const card = document.createElement("div");
    card.className = `cursor-pointer p-4 rounded-2xl border transition-all flex items-center justify-between ${
      isSelected
        ? "bg-dark-750 border-brand-500 ring-2 ring-brand-500/30 shadow-lg shadow-brand-500/10"
        : "bg-dark-800 border-dark-700 hover:border-dark-600 hover:bg-dark-750"
    }`;
    card.onclick = () => selectCrypto(c.symbol);

    const trainedBadge = c.is_trained
      ? `<span class="inline-flex items-center text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Trained</span>`
      : `<span class="inline-flex items-center text-xs font-semibold px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">Needs Train</span>`;

    card.innerHTML = `
      <div class="flex items-center space-x-3">
        <div class="w-12 h-12 rounded-xl flex items-center justify-center text-2xl font-bold bg-dark-900 border border-dark-700 shadow" style="color: ${c.color}">
          ${c.icon}
        </div>
        <div>
          <div class="flex items-center space-x-2">
            <span class="font-bold text-white">${c.name}</span>
            <span class="text-xs text-slate-400 font-mono">${c.symbol}</span>
          </div>
          <div class="text-xs text-slate-400 mt-0.5">Pair: ${c.pair}</div>
        </div>
      </div>
      <div class="text-right">
        ${trainedBadge}
      </div>
    `;
    container.appendChild(card);
  });
}

// Select a Crypto
async function selectCrypto(symbol) {
  if (selectedCrypto === symbol) return;
  selectedCrypto = symbol;
  renderCryptoCards();
  await loadCryptoData();
}

// Load Data & Model for Selected Crypto
async function loadCryptoData() {
  const crypto = cryptos.find((c) => c.symbol === selectedCrypto) || {
    name: selectedCrypto,
    color: "#0ea5e9",
  };

  document.getElementById("chart-crypto-name").textContent = crypto.name;
  document.getElementById("forecast-crypto-name").textContent = crypto.name;

  await Promise.all([
    loadHistory(180),
    loadModelInfo(),
  ]);
}

// Load Historical Prices
async function loadHistory(days = 180) {
  // Update Range button styles
  document.querySelectorAll(".history-range-btn").forEach((btn) => {
    if (parseInt(btn.getAttribute("data-days")) === days) {
      btn.className = "history-range-btn px-3 py-1 text-xs rounded-lg bg-brand-600 text-white";
    } else {
      btn.className = "history-range-btn px-3 py-1 text-xs rounded-lg bg-dark-700 hover:bg-dark-600 text-slate-300";
    }
  });

  try {
    const res = await fetch(`/api/crypto/${selectedCrypto}/history?days=${days}`);
    const data = await res.json();
    currentHistoryData = data.history || [];

    if (currentHistoryData.length > 0) {
      const lastPoint = currentHistoryData[currentHistoryData.length - 1];
      document.getElementById("stat-current-price").textContent = `$${lastPoint.close.toLocaleString()}`;
      document.getElementById("stat-price-date").textContent = `Last update: ${lastPoint.date}`;
    }

    renderHistoryChart(currentHistoryData);
  } catch (err) {
    console.error("Failed to load history:", err);
    showToast("Failed to fetch historical data.", "error");
  }
}

// Render Historical Chart
function renderHistoryChart(history) {
  const ctx = document.getElementById("historyChart").getContext("2d");
  const labels = history.map((d) => d.date);
  const prices = history.map((d) => d.close);

  // Compute 7-day MA for chart
  const ma7 = prices.map((_, idx, arr) => {
    if (idx < 6) return null;
    const slice = arr.slice(idx - 6, idx + 1);
    return slice.reduce((a, b) => a + b, 0) / 7;
  });

  const crypto = cryptos.find((c) => c.symbol === selectedCrypto) || { color: "#38bdf8" };

  if (historyChart) {
    historyChart.destroy();
  }

  // Create gradient
  const gradient = ctx.createLinearGradient(0, 0, 0, 300);
  gradient.addColorStop(0, `${crypto.color}44`);
  gradient.addColorStop(1, `${crypto.color}00`);

  historyChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: `${selectedCrypto} Price (USD)`,
          data: prices,
          borderColor: crypto.color,
          backgroundColor: gradient,
          fill: true,
          borderWidth: 2,
          pointRadius: 0,
          pointHoverRadius: 6,
          tension: 0.15,
        },
        {
          label: "7-Day Moving Avg",
          data: ma7,
          borderColor: "#94a3b8",
          borderWidth: 1.5,
          borderDash: [4, 4],
          pointRadius: 0,
          fill: false,
          tension: 0.15,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: "index",
        intersect: false,
      },
      plugins: {
        legend: {
          display: true,
          labels: { color: "#94a3b8", font: { size: 12 } },
        },
        tooltip: {
          backgroundColor: "#1e293b",
          titleColor: "#f8fafc",
          bodyColor: "#f8fafc",
          borderColor: "#334155",
          borderWidth: 1,
          callbacks: {
            label: (item) => `${item.dataset.label}: $${item.raw ? item.raw.toLocaleString() : "N/A"}`,
          },
        },
      },
      scales: {
        x: {
          grid: { color: "#1e293b" },
          ticks: { color: "#64748b", maxTicksLimit: 10 },
        },
        y: {
          grid: { color: "#1e293b" },
          ticks: {
            color: "#64748b",
            callback: (val) => `$${val.toLocaleString()}`,
          },
        },
      },
    },
  });
}

// Load Model Info
async function loadModelInfo() {
  try {
    const res = await fetch(`/api/crypto/${selectedCrypto}/model`);
    const data = await res.json();

    const statusEl = document.getElementById("stat-model-status");
    const trainedAtEl = document.getElementById("stat-trained-at");
    const mapeEl = document.getElementById("stat-mape");
    const accEl = document.getElementById("stat-accuracy");
    const metricsContainer = document.getElementById("metrics-content");

    if (data.is_trained && data.data) {
      const meta = data.data;
      statusEl.innerHTML = `<span class="px-2.5 py-1 text-xs font-semibold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Trained</span>`;
      trainedAtEl.textContent = `Trained: ${new Date(meta.trained_at).toLocaleString()}`;
      mapeEl.textContent = `${meta.metrics.mape}%`;
      accEl.textContent = `${meta.metrics.directional_accuracy_pct}%`;

      // Render feature importances & details
      let featHtml = Object.entries(meta.top_features || {})
        .slice(0, 6)
        .map(([k, v]) => {
          return `
            <div class="space-y-1">
              <div class="flex justify-between text-xs">
                <span class="font-mono text-slate-300">${k}</span>
                <span class="text-slate-400">${v} splits</span>
              </div>
              <div class="w-full bg-dark-900 rounded-full h-1.5 overflow-hidden">
                <div class="bg-gradient-to-r from-brand-500 to-purple-500 h-1.5 rounded-full" style="width: ${Math.min(v * 3, 100)}%"></div>
              </div>
            </div>
          `;
        })
        .join("");

      metricsContainer.innerHTML = `
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
          <div class="bg-dark-900 p-3 rounded-xl border border-dark-700">
            <span class="text-xs text-slate-400">RMSE</span>
            <p class="text-base font-bold text-white">$${meta.metrics.rmse.toLocaleString()}</p>
          </div>
          <div class="bg-dark-900 p-3 rounded-xl border border-dark-700">
            <span class="text-xs text-slate-400">MAE</span>
            <p class="text-base font-bold text-white">$${meta.metrics.mae.toLocaleString()}</p>
          </div>
          <div class="bg-dark-900 p-3 rounded-xl border border-dark-700">
            <span class="text-xs text-slate-400">R² Score</span>
            <p class="text-base font-bold text-white">${meta.metrics.r2_score}</p>
          </div>
          <div class="bg-dark-900 p-3 rounded-xl border border-dark-700">
            <span class="text-xs text-slate-400">Samples</span>
            <p class="text-base font-bold text-white">${meta.samples_total}</p>
          </div>
        </div>
        <div class="space-y-2">
          <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Top Technical Feature Drivers:</span>
          ${featHtml}
        </div>
      `;
    } else {
      statusEl.innerHTML = `<span class="px-2.5 py-1 text-xs font-semibold rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">Not Trained</span>`;
      trainedAtEl.textContent = "Click train below to create model";
      mapeEl.textContent = "--";
      accEl.textContent = "--";
      metricsContainer.innerHTML = `<div class="text-center py-8 text-slate-500 text-sm">No model trained yet for ${selectedCrypto}. Click below to fetch data and train.</div>`;
    }
  } catch (err) {
    console.error("Failed to load model info:", err);
  }
}

// Train Current Model
async function trainCurrentModel() {
  const trainBtn = document.getElementById("train-btn");
  const origHtml = trainBtn.innerHTML;

  trainBtn.disabled = true;
  trainBtn.innerHTML = `
    <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
    </svg>
    <span>Training LightGBM Model...</span>
  `;

  try {
    const res = await fetch(`/api/crypto/${selectedCrypto}/train`, { method: "POST" });
    const data = await res.json();

    if (data.success) {
      showToast(`LightGBM model for ${selectedCrypto} trained successfully!`, "success");
      await loadCryptos();
      await loadModelInfo();
    } else {
      showToast(data.detail || "Training failed", "error");
    }
  } catch (err) {
    console.error("Training request failed:", err);
    showToast("Error communicating with training backend.", "error");
  } finally {
    trainBtn.disabled = false;
    trainBtn.innerHTML = origHtml;
  }
}

// Horizon Controls
function updateHorizon(val) {
  horizonDays = parseInt(val);
  document.getElementById("horizon-display").textContent = horizonDays;
  updatePresetButtons();
}

function setHorizon(days) {
  horizonDays = days;
  document.getElementById("horizon-slider").value = days;
  document.getElementById("horizon-display").textContent = days;
  updatePresetButtons();
}

function updatePresetButtons() {
  document.querySelectorAll(".preset-btn").forEach((btn) => {
    const btnDays = parseInt(btn.textContent);
    if (btnDays === horizonDays) {
      btn.className = "preset-btn px-3 py-1 text-xs rounded-lg bg-brand-600 text-white";
    } else {
      btn.className = "preset-btn px-3 py-1 text-xs rounded-lg bg-dark-700 hover:bg-dark-600 text-slate-300";
    }
  });
}

// Run Price Forecast
async function runForecast() {
  const predictBtn = document.getElementById("predict-btn");
  const origHtml = predictBtn.innerHTML;

  predictBtn.disabled = true;
  predictBtn.innerHTML = `
    <svg class="animate-spin -ml-1 mr-2 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
    </svg>
    <span>Forecasting ${horizonDays} Days...</span>
  `;

  try {
    const res = await fetch(`/api/crypto/${selectedCrypto}/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ horizon_days: horizonDays }),
    });

    const data = await res.json();
    if (data.success && data.forecast) {
      renderForecastResults(data.forecast);
      showToast(`Forecast for ${selectedCrypto} (${horizonDays} days) generated!`, "success");
    } else {
      showToast(data.detail || "Forecast failed", "error");
    }
  } catch (err) {
    console.error("Prediction request failed:", err);
    showToast("Error generating forecast.", "error");
  } finally {
    predictBtn.disabled = false;
    predictBtn.innerHTML = origHtml;
  }
}

// Render Forecast Output
function renderForecastResults(fc) {
  // Reveal containers
  document.getElementById("forecast-summary-card").classList.remove("hidden");
  document.getElementById("forecast-chart-container").classList.remove("hidden");
  document.getElementById("forecast-table-container").classList.remove("hidden");

  // Summary Metrics
  document.getElementById("sum-start-price").textContent = `$${fc.current_price.toLocaleString()}`;
  document.getElementById("sum-start-date").textContent = `Base: ${fc.current_date}`;
  document.getElementById("sum-end-price").textContent = `$${fc.final_predicted_price.toLocaleString()}`;
  document.getElementById("sum-end-date").textContent = `Target: ${fc.predictions[fc.predictions.length - 1].date}`;

  const returnPctEl = document.getElementById("sum-return-pct");
  const isPositive = fc.total_change_pct >= 0;
  returnPctEl.textContent = `${isPositive ? "+" : ""}${fc.total_change_pct}%`;
  returnPctEl.className = `text-2xl font-bold mt-1 ${isPositive ? "text-emerald-400" : "text-rose-400"}`;

  const returnUsdEl = document.getElementById("sum-return-usd");
  returnUsdEl.textContent = `${isPositive ? "+" : ""}$${fc.total_change_usd.toLocaleString()} per coin`;

  const trendBadge = document.getElementById("sum-trend-badge");
  if (fc.trend === "bullish") {
    trendBadge.className = "mt-2 inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
    trendBadge.innerHTML = `<span class="mr-1.5">↗</span> Bullish Trend`;
  } else if (fc.trend === "bearish") {
    trendBadge.className = "mt-2 inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20";
    trendBadge.innerHTML = `<span class="mr-1.5">↘</span> Bearish Trend`;
  } else {
    trendBadge.className = "mt-2 inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-slate-500/10 text-slate-400 border border-slate-500/20";
    trendBadge.innerHTML = `<span class="mr-1.5">→</span> Neutral / Sideways`;
  }

  // Render Forecast Chart
  renderForecastChart(fc);

  // Render Table
  renderForecastTable(fc.predictions);

  if (window.lucide) lucide.createIcons();
}

// Render Forecast Chart
function renderForecastChart(fc) {
  const ctx = document.getElementById("forecastChart").getContext("2d");

  // Historical labels and points
  const histDates = fc.historical.map((h) => h.date);
  const histPrices = fc.historical.map((h) => h.price);

  // Forecast points
  const predDates = fc.predictions.map((p) => p.date);
  const predPrices = fc.predictions.map((p) => p.predicted_price);
  const lowerBounds = fc.predictions.map((p) => p.lower_bound);
  const upperBounds = fc.predictions.map((p) => p.upper_bound);

  // Connect last historical point to first prediction point
  const allDates = [...histDates, ...predDates];

  const historicalSeries = [...histPrices, ...Array(predDates.length).fill(null)];
  const predictionSeries = [...Array(histDates.length - 1).fill(null), histPrices[histPrices.length - 1], ...predPrices];
  const upperSeries = [...Array(histDates.length - 1).fill(null), histPrices[histPrices.length - 1], ...upperBounds];
  const lowerSeries = [...Array(histDates.length - 1).fill(null), histPrices[histPrices.length - 1], ...lowerBounds];

  if (forecastChart) {
    forecastChart.destroy();
  }

  forecastChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: allDates,
      datasets: [
        {
          label: "Historical Price",
          data: historicalSeries,
          borderColor: "#94a3b8",
          borderWidth: 2,
          pointRadius: 0,
          fill: false,
          tension: 0.1,
        },
        {
          label: "Predicted Price",
          data: predictionSeries,
          borderColor: "#38bdf8",
          borderWidth: 2.5,
          borderDash: [5, 5],
          pointRadius: 3,
          pointBackgroundColor: "#38bdf8",
          fill: false,
          tension: 0.1,
        },
        {
          label: "Upper Bound (+95% Confidence)",
          data: upperSeries,
          borderColor: "rgba(56, 189, 248, 0.2)",
          backgroundColor: "rgba(56, 189, 248, 0.1)",
          fill: "+1",
          borderWidth: 1,
          pointRadius: 0,
          tension: 0.1,
        },
        {
          label: "Lower Bound (-95% Confidence)",
          data: lowerSeries,
          borderColor: "rgba(56, 189, 248, 0.2)",
          backgroundColor: "transparent",
          fill: false,
          borderWidth: 1,
          pointRadius: 0,
          tension: 0.1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          display: true,
          labels: { color: "#94a3b8", font: { size: 12 } },
        },
        tooltip: {
          backgroundColor: "#1e293b",
          titleColor: "#f8fafc",
          bodyColor: "#f8fafc",
          borderColor: "#334155",
          borderWidth: 1,
          callbacks: {
            label: (item) => {
              if (item.raw === null) return "";
              return `${item.dataset.label}: $${Number(item.raw).toLocaleString()}`;
            },
          },
        },
      },
      scales: {
        x: {
          grid: { color: "#1e293b" },
          ticks: { color: "#64748b", maxTicksLimit: 12 },
        },
        y: {
          grid: { color: "#1e293b" },
          ticks: {
            color: "#64748b",
            callback: (val) => `$${val.toLocaleString()}`,
          },
        },
      },
    },
  });
}

// Render Table
function renderForecastTable(predictions) {
  const tbody = document.getElementById("forecast-table-body");
  tbody.innerHTML = "";

  predictions.forEach((p) => {
    const isUp = p.predicted_return_pct >= 0;
    const isTotUp = p.cumulative_change_pct >= 0;
    const tr = document.createElement("tr");
    tr.className = "hover:bg-dark-750 transition-colors";
    tr.innerHTML = `
      <td class="py-3 px-4 font-bold text-slate-300">Day ${p.step}</td>
      <td class="py-3 px-4 text-slate-400">${p.date}</td>
      <td class="py-3 px-4 font-bold text-white">$${p.predicted_price.toLocaleString()}</td>
      <td class="py-3 px-4 ${isUp ? "text-emerald-400" : "text-rose-400"}">
        ${isUp ? "+" : ""}${p.predicted_return_pct}%
      </td>
      <td class="py-3 px-4 ${isTotUp ? "text-emerald-400" : "text-rose-400"}">
        ${isTotUp ? "+" : ""}${p.cumulative_change_pct}%
      </td>
      <td class="py-3 px-4 text-slate-400">$${p.lower_bound.toLocaleString()}</td>
      <td class="py-3 px-4 text-slate-400">$${p.upper_bound.toLocaleString()}</td>
    `;
    tbody.appendChild(tr);
  });
}
