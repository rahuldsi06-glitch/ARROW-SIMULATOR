// Arrow.Trade Algo Trader Web Interface
const API = {
  getAuthStatus: () => fetch("/api/auth/status").then(r => r.json()),
  login: (data) => fetch("/api/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) }).then(r => r.json()),
  setToken: (token) => fetch("/api/auth/set-token", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token }) }).then(r => r.json()),
  logout: () => fetch("/api/auth/logout", { method: "POST" }).then(r => r.json()),
  updateConfig: (data) => fetch("/api/auth/config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) }).then(r => r.json()),
  getLimits: () => fetch("/api/user/limits").then(r => r.json()),
  getPositions: () => fetch("/api/portfolio/positions").then(r => r.json()),
  getHoldings: () => fetch("/api/portfolio/holdings").then(r => r.json()),
  getOrders: () => fetch("/api/orders/book").then(r => r.json()),
  getTrades: () => fetch("/api/orders/trades").then(r => r.json()),
  placeOrder: (data) => fetch("/api/orders/place", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) }).then(r => r.json()),
  cancelOrder: (order_id) => fetch("/api/orders/cancel", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ order_id }) }).then(r => r.json()),
  checkMargin: (data) => fetch("/api/orders/margin", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) }).then(r => r.json()),
  getQuote: async (symbol, exchange = "NSE") => {
    const r = await fetch(`/api/market/quote?symbol=${encodeURIComponent(symbol)}&exchange=${exchange}`);
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || "Failed to fetch quote");
    if (data.message && data.message === "not found") throw new Error(`Symbol '${symbol}' not found on ${exchange}`);
    return data;
  },
  getAlgos: () => fetch("/api/algo/list").then(r => r.json()),
  startAlgo: (name) => fetch(`/api/algo/start?name=${encodeURIComponent(name)}`, { method: "POST" }).then(r => r.json()),
  stopAlgo: (name) => fetch(`/api/algo/stop?name=${encodeURIComponent(name)}`, { method: "POST" }).then(r => r.json()),
};

let currentTab = "overview";
let isAuthenticated = false;
let ws = null;
const liveTicks = {};

// DOM Elements
const authStatusBadge = document.getElementById("auth-status-badge");
const authUserSpan = document.getElementById("auth-user-span");

// Tab Navigation
function setupTabs() {
  document.querySelectorAll(".nav-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".nav-tab").forEach(t => t.classList.remove("active"));
      document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
      tab.classList.add("active");
      currentTab = tab.dataset.tab;
      document.getElementById(`tab-${currentTab}`).classList.add("active");
      loadTabData(currentTab);
    });
  });
}

async function checkAuth() {
  try {
    const res = await API.getAuthStatus();
    isAuthenticated = res.authenticated;
    if (res.authenticated) {
      authStatusBadge.className = "badge badge-green";
      authStatusBadge.textContent = "● Authenticated";
      const u = res.user || {};
      authUserSpan.textContent = `${u.name || "Logged In"} (${u.userID || res.app_id || ""})`;
      document.getElementById("auth-banner").style.display = "none";
    } else {
      authStatusBadge.className = "badge badge-red";
      authStatusBadge.textContent = "● Not Connected";
      authUserSpan.textContent = "Guest";
      document.getElementById("auth-banner").style.display = "block";
    }
  } catch (e) {
    console.error("Auth check failed:", e);
  }
}

function loadTabData(tab) {
  if (tab === "overview") loadOverview();
  else if (tab === "portfolio") loadPortfolio();
  else if (tab === "orders") loadOrders();
  else if (tab === "market") loadMarket();
  else if (tab === "algo") loadAlgos();
}

async function loadOverview() {
  if (!isAuthenticated) return;
  try {
    const limits = await API.getLimits();
    const margin = limits.margin || {};
    const avail = parseFloat(margin.totalAvailableMargin || margin.usableMargin || margin.allocated || margin.available_margin || 0);
    const used = parseFloat(margin.utilized || margin.cashUsed || margin.used_margin || 0);
    const collateral = parseFloat(margin.totalNoncash || margin.totalCashEq || margin.collateral || 0);

    document.getElementById("metric-available-margin").textContent = `₹${Number(avail).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
    document.getElementById("metric-used-margin").textContent = `₹${Number(used).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
    document.getElementById("metric-collateral").textContent = `₹${Number(collateral).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
  } catch (e) {
    console.warn("Could not load limits:", e);
  }
}

async function loadPortfolio() {
  if (!isAuthenticated) return;
  const posTbody = document.querySelector("#positions-table tbody");
  const holdTbody = document.querySelector("#holdings-table tbody");

  try {
    const positions = await API.getPositions();
    posTbody.innerHTML = "";
    if (!positions || positions.length === 0) {
      posTbody.innerHTML = `<tr><td colspan="6" class="text-center" style="color:var(--text-muted)">No open positions</td></tr>`;
    } else {
      positions.forEach(p => {
        const pnl = parseFloat(p.pnl || p.urmtom || 0);
        const pnlClass = pnl >= 0 ? "text-green" : "text-red";
        posTbody.innerHTML += `
          <tr>
            <td class="mono font-bold">${p.symbol || p.tradingSymbol || "-"}</td>
            <td>${p.product || "-"}</td>
            <td class="text-right mono">${p.netQty || p.netqty || 0}</td>
            <td class="text-right mono">₹${parseFloat(p.buyAvgPrice || p.avgPrice || 0).toFixed(2)}</td>
            <td class="text-right mono">₹${parseFloat(p.ltp || 0).toFixed(2)}</td>
            <td class="text-right mono ${pnlClass}">₹${pnl.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
          </tr>
        `;
      });
    }
  } catch (e) {
    posTbody.innerHTML = `<tr><td colspan="6" class="text-red">Error loading positions: ${e.message}</td></tr>`;
  }

  try {
    const holdings = await API.getHoldings();
    holdTbody.innerHTML = "";
    if (!holdings || holdings.length === 0) {
      holdTbody.innerHTML = `<tr><td colspan="7" class="text-center" style="color:var(--text-muted)">No holdings found</td></tr>`;
    } else {
      holdings.forEach(h => {
        const qty = parseInt(h.quantity || h.holdingsQty || 0);
        const cost = parseFloat(h.averagePrice || h.price || 0);
        const ltp = parseFloat(h.ltp || 0);
        const val = qty * ltp;
        const pnl = (ltp - cost) * qty;
        const pnlClass = pnl >= 0 ? "text-green" : "text-red";
        holdTbody.innerHTML += `
          <tr>
            <td class="mono font-bold">${h.symbol || h.tradingSymbol || "-"}</td>
            <td>${h.exchange || "NSE"}</td>
            <td class="text-right mono">${qty}</td>
            <td class="text-right mono">₹${cost.toFixed(2)}</td>
            <td class="text-right mono">₹${ltp.toFixed(2)}</td>
            <td class="text-right mono">₹${val.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
            <td class="text-right mono ${pnlClass}">₹${pnl.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
          </tr>
        `;
      });
    }
  } catch (e) {
    holdTbody.innerHTML = `<tr><td colspan="7" class="text-red">Error loading holdings: ${e.message}</td></tr>`;
  }
}

async function loadOrders() {
  if (!isAuthenticated) return;
  const tbody = document.querySelector("#orders-table tbody");
  tbody.innerHTML = `<tr><td colspan="8" style="color:var(--text-muted)">Loading orders...</td></tr>`;

  try {
    const orders = await API.getOrders();
    tbody.innerHTML = "";
    if (!orders || orders.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" class="text-center" style="color:var(--text-muted)">No orders placed today</td></tr>`;
      return;
    }

    orders.forEach(o => {
      const side = (o.transactionType || o.transType || "").toUpperCase();
      const isBuy = side === "B" || side === "BUY";
      const sideClass = isBuy ? "text-green" : "text-red";
      const status = (o.status || o.orderStatus || "").toUpperCase();
      const orderId = o.orderNo || o.orderId || "";
      const canCancel = ["OPEN", "PENDING", "TRIGGER PENDING"].includes(status);

      tbody.innerHTML += `
        <tr>
          <td class="mono" style="color:var(--text-muted)">${orderId}</td>
          <td class="mono font-bold">${o.symbol || o.tradingSymbol || "-"}</td>
          <td class="${sideClass} font-bold">${isBuy ? "BUY" : "SELL"}</td>
          <td>${o.orderType || "LIMIT"}</td>
          <td class="text-right mono">${o.filledQuantity || 0} / ${o.quantity || 0}</td>
          <td class="text-right mono">₹${parseFloat(o.price || 0).toFixed(2)}</td>
          <td><span class="badge ${status === "COMPLETE" ? "badge-green" : status === "REJECTED" ? "badge-red" : "badge-yellow"}">${status}</span></td>
          <td class="text-right">
            ${canCancel ? `<button class="btn btn-sm btn-secondary" onclick="cancelOrder('${orderId}')">Cancel</button>` : "-"}
          </td>
        </tr>
      `;
    });
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="8" class="text-red">Error: ${e.message}</td></tr>`;
  }
}

window.cancelOrder = async function(orderId) {
  if (!confirm(`Cancel order ${orderId}?`)) return;
  try {
    const res = await API.cancelOrder(orderId);
    alert(`Order cancelled: ${res.result || "Success"}`);
    loadOrders();
  } catch (e) {
    alert(`Failed to cancel: ${e.message}`);
  }
};

// Order form & Margin preview
let currentSide = "BUY";
function setupOrderForm() {
  const buyBtn = document.getElementById("order-side-buy");
  const sellBtn = document.getElementById("order-side-sell");
  const submitBtn = document.getElementById("order-submit-btn");

  buyBtn.addEventListener("click", () => {
    currentSide = "BUY";
    buyBtn.className = "btn btn-buy";
    sellBtn.className = "btn btn-secondary";
    submitBtn.className = "btn btn-buy";
    submitBtn.textContent = "Place BUY Order";
  });

  sellBtn.addEventListener("click", () => {
    currentSide = "SELL";
    sellBtn.className = "btn btn-sell";
    buyBtn.className = "btn btn-secondary";
    submitBtn.className = "btn btn-sell";
    submitBtn.textContent = "Place SELL Order";
  });

  document.getElementById("btn-calc-margin").addEventListener("click", async () => {
    const symbol = document.getElementById("order-symbol").value.trim().toUpperCase();
    const qty = parseInt(document.getElementById("order-qty").value) || 1;
    const price = parseFloat(document.getElementById("order-price").value) || 0;
    const product = document.getElementById("order-product").value;
    const order_type = document.getElementById("order-type").value;
    const exchange = document.getElementById("order-exchange").value;

    const preview = document.getElementById("margin-preview");
    preview.textContent = "Calculating margin...";

    try {
      const res = await API.checkMargin({
        symbol,
        quantity: qty,
        price,
        exchange,
        transaction_type: currentSide,
        order_type,
        product,
      });
      const req = res.requiredMargin || res.margin || res.initial_margin || 0;
      preview.textContent = `Required Margin: ₹${Number(req).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
    } catch (e) {
      preview.textContent = `Margin estimate: ₹${(qty * (price || 1)).toLocaleString("en-IN")}`;
    }
  });

  document.getElementById("order-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!isAuthenticated) {
      alert("Please login first to place broker orders.");
      return;
    }

    const symbol = document.getElementById("order-symbol").value.trim().toUpperCase();
    const qty = parseInt(document.getElementById("order-qty").value);
    const price = parseFloat(document.getElementById("order-price").value) || 0;
    const product = document.getElementById("order-product").value;
    const order_type = document.getElementById("order-type").value;
    const exchange = document.getElementById("order-exchange").value;

    if (!confirm(`Confirm ${currentSide} order: ${qty} x ${symbol} @ ₹${price}?`)) return;

    try {
      const res = await API.placeOrder({
        symbol,
        quantity: qty,
        price,
        exchange,
        transaction_type: currentSide,
        order_type,
        product,
      });
      alert(`Order Placed! Order ID: ${res.order_id}`);
      loadOrders();
      loadOverview();
    } catch (err) {
      alert(`Order placement failed: ${err.message}`);
    }
  });
}

// Quote Lookup
function setupMarketWatch() {
  const quoteBtn = document.getElementById("btn-fetch-quote");
  const symInput = document.getElementById("quote-search-symbol");
  const exSelect = document.getElementById("quote-search-exchange");
  const card = document.getElementById("quote-result-card");

  async function doFetch() {
    const sym = symInput.value.trim().toUpperCase();
    const ex = exSelect.value;
    if (!sym) {
      alert("Please enter a symbol (e.g. RELIANCE, TCS, INFY)");
      return;
    }

    quoteBtn.disabled = true;
    quoteBtn.textContent = "Fetching...";

    try {
      const quote = await API.getQuote(sym, ex);
      document.getElementById("qr-symbol").textContent = `${quote.symbol || sym} (${ex})`;
      const ltp = parseFloat(quote.ltp || 0) / 100.0;
      const chg = parseFloat(quote.net_change || quote.netChange || quote.change || 0);
      const chgEl = document.getElementById("qr-change");
      chgEl.textContent = `${chg >= 0 ? "+" : ""}${chg.toFixed(2)}%`;
      chgEl.className = `metric-sub ${chg >= 0 ? "text-green" : "text-red"}`;

      document.getElementById("qr-ltp").textContent = `₹${ltp.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
      document.getElementById("qr-open").textContent = `₹${(parseFloat(quote.open || 0) / 100.0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
      document.getElementById("qr-high").textContent = `₹${(parseFloat(quote.high || 0) / 100.0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
      document.getElementById("qr-low").textContent = `₹${(parseFloat(quote.low || 0) / 100.0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
      document.getElementById("qr-close").textContent = `₹${(parseFloat(quote.close || 0) / 100.0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
      document.getElementById("qr-volume").textContent = Number(quote.volume || 0).toLocaleString("en-IN");
      card.style.display = "block";
    } catch (e) {
      alert(`Quote Error: ${e.message}`);
    } finally {
      quoteBtn.disabled = false;
      quoteBtn.textContent = "Fetch Quote";
    }
  }

  quoteBtn.addEventListener("click", doFetch);
  symInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      doFetch();
    }
  });
}

function loadMarket() {
  // Can trigger a refresh if a symbol is already filled
}

// Algo Strategies
async function loadAlgos() {
  const container = document.getElementById("algos-container");
  container.innerHTML = "Loading algos...";
  try {
    const list = await API.getAlgos();
    container.innerHTML = "";
    if (!list || list.length === 0) {
      container.innerHTML = `<p style="color:var(--text-muted)">No registered algo strategies found.</p>`;
      return;
    }

    list.forEach(strat => {
      const isRun = strat.is_running;
      const logs = (strat.recent_logs || []).map(l => `[${new Date(l.timestamp * 1000).toLocaleTimeString()}] ${l.message}`).join("\n");

      const card = document.createElement("div");
      card.className = "card";
      card.innerHTML = `
        <div class="card-title">
          <div>
            <span>${strat.name}</span>
            <span class="badge ${isRun ? "badge-green" : "badge-red"}" style="margin-left:10px;">${isRun ? "RUNNING" : "STOPPED"}</span>
          </div>
          <div>
            <button class="btn btn-sm ${isRun ? "btn-sell" : "btn-buy"}" onclick="toggleAlgo('${strat.name}', ${isRun})">
              ${isRun ? "Stop Strategy" : "Start Strategy"}
            </button>
          </div>
        </div>
        <p style="font-size:12px; color:var(--text-secondary); margin-bottom:10px;">
          Symbols: <strong>${strat.symbols.join(", ")}</strong> | Mode: <strong>${strat.params.paper_trading ? "Paper Trading" : "Live Broker"}</strong>
        </p>
        <div class="terminal-box" style="height:140px;">${logs || "No logs yet. Click start to begin."}</div>
      `;
      container.appendChild(card);
    });
  } catch (e) {
    container.innerHTML = `<p class="text-red">Error: ${e.message}</p>`;
  }
}

window.toggleAlgo = async function(name, isRunning) {
  try {
    if (isRunning) {
      await API.stopAlgo(name);
    } else {
      await API.startAlgo(name);
    }
    loadAlgos();
  } catch (e) {
    alert(`Failed to toggle strategy: ${e.message}`);
  }
};

// WebSocket Live Stream
function setupWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/ticks`;
  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log("WebSocket connected");
  };

  ws.onmessage = (evt) => {
    try {
      const msg = JSON.parse(evt.data);
      if (msg.type === "tick") {
        const tick = msg.data;
        liveTicks[tick.token] = tick;
        renderLiveTicker(tick);
      }
    } catch (e) {}
  };

  ws.onclose = () => {
    console.warn("WebSocket disconnected, reconnecting in 3s...");
    setTimeout(setupWebSocket, 3000);
  };
}

function renderLiveTicker(tick) {
  const container = document.getElementById("live-ticker-list");
  if (!container) return;
  let item = document.getElementById(`tick-${tick.token}`);
  if (!item) {
    item = document.createElement("div");
    item.id = `tick-${tick.token}`;
    item.className = "ticker-item";
    container.prepend(item);
  }
  const chg = parseFloat(tick.net_change || 0);
  item.innerHTML = `
    <span class="mono">Token ${tick.token}</span>
    <span class="mono font-bold">₹${parseFloat(tick.ltp || 0).toFixed(2)}</span>
    <span class="mono ${chg >= 0 ? "text-green" : "text-red"}">${chg >= 0 ? "+" : ""}${chg.toFixed(2)}%</span>
  `;
}

// Login form handlers
function setupAuthForms() {
  document.getElementById("btn-login-totp").addEventListener("click", async () => {
    const user_id = document.getElementById("login-user-id").value.trim();
    const password = document.getElementById("login-password").value.trim();
    const totp_secret = document.getElementById("login-totp-secret").value.trim();
    const app_id = document.getElementById("login-app-id").value.trim();
    const app_secret = document.getElementById("login-app-secret").value.trim();

    if (!user_id || !password || !totp_secret) {
      alert("Please fill all credentials");
      return;
    }

    try {
      const res = await API.login({ user_id, password, totp_secret, app_id, app_secret, save_env: true });
      alert("Logged in successfully!");
      checkAuth();
      loadTabData(currentTab);
    } catch (e) {
      alert(`Login failed: ${e.message}`);
    }
  });

  document.getElementById("btn-set-token").addEventListener("click", async () => {
    const token = document.getElementById("login-manual-token").value.trim();
    if (!token) return alert("Please enter token");
    try {
      await API.setToken(token);
      alert("Token verified and saved!");
      checkAuth();
      loadTabData(currentTab);
    } catch (e) {
      alert(`Token error: ${e.message}`);
    }
  });

  document.getElementById("btn-logout").addEventListener("click", async () => {
    if (!confirm("Confirm logout?")) return;
    await API.logout();
    checkAuth();
    loadTabData(currentTab);
  });
}

// Init
window.addEventListener("DOMContentLoaded", () => {
  setupTabs();
  setupOrderForm();
  setupAuthForms();
  setupMarketWatch();
  setupWebSocket();
  checkAuth().then(() => loadTabData(currentTab));
});
