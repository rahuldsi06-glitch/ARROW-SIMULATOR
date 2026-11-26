/**
 * ARROW TRADE PRO 2.0 // Authentication, Behavior Tracking & Tradeify-Style Profile Calendar
 */
(function (window) {
  "use strict";

  class AuthProfileManager {
    constructor(gameApp) {
      this.app = gameApp;
      this.tokenKey = "arrow_auth_token";
      this.userKey = "arrow_auth_user";
      this.historyKey = "arrow_user_trade_history";
      this.token = localStorage.getItem(this.tokenKey) || null;
      this.user = null;
      try {
        const raw = localStorage.getItem(this.userKey);
        if (raw) this.user = JSON.parse(raw);
      } catch (e) {}

      const now = new Date();
      this.calYear = now.getFullYear();
      this.calMonth = now.getMonth(); // 0-indexed
      this.selectedDateFilter = null;
      this.profileData = null;
    }

    init() {
      this._cacheDOM();
      this._bindEvents();
      this._checkSession();
    }

    _cacheDOM() {
      this.modalAuth = document.getElementById("modal-auth");
      this.tabSignIn = document.getElementById("auth-tab-signin");
      this.tabSignUp = document.getElementById("auth-tab-signup");
      this.formSignIn = document.getElementById("auth-form-signin");
      this.formSignUp = document.getElementById("auth-form-signup");
      this.authError = document.getElementById("auth-error-msg");

      this.btnProfileTrigger = document.getElementById("btn-user-profile");
      this.lblHeaderUsername = document.getElementById("header-username");

      this.modalProfile = document.getElementById("modal-user-profile");
      this.btnCloseProfile = document.getElementById("btn-close-profile");
      this.btnLogout = document.getElementById("btn-profile-logout");
      this.calPrev = document.getElementById("cal-prev-month");
      this.calNext = document.getElementById("cal-next-month");
      this.calMonthLabel = document.getElementById("cal-month-label");
      this.calGrid = document.getElementById("tradeify-calendar-grid");
      this.tradesTbody = document.getElementById("profile-trades-tbody");
      this.btnClearDateFilter = document.getElementById("btn-clear-date-filter");
    }

    _bindEvents() {
      if (this.tabSignIn) {
        this.tabSignIn.addEventListener("click", () => this._switchAuthTab("signin"));
      }
      if (this.tabSignUp) {
        this.tabSignUp.addEventListener("click", () => this._switchAuthTab("signup"));
      }
      if (this.formSignIn) {
        this.formSignIn.addEventListener("submit", (e) => {
          e.preventDefault();
          this.handleSignIn();
        });
      }
      if (this.formSignUp) {
        this.formSignUp.addEventListener("submit", (e) => {
          e.preventDefault();
          this.handleSignUp();
        });
      }
      if (this.btnProfileTrigger) {
        this.btnProfileTrigger.addEventListener("click", () => {
          if (!this.token || !this.user) {
            this.openAuthModal("signin");
          } else {
            this.openProfileModal();
          }
        });
      }
      if (this.btnCloseProfile) {
        this.btnCloseProfile.addEventListener("click", () => {
          if (this.modalProfile) this.modalProfile.classList.add("hidden");
        });
      }
      if (this.btnLogout) {
        this.btnLogout.addEventListener("click", () => this.logout());
      }
      if (this.calPrev) {
        this.calPrev.addEventListener("click", () => {
          this.calMonth--;
          if (this.calMonth < 0) {
            this.calMonth = 11;
            this.calYear--;
          }
          this.renderCalendar();
        });
      }
      if (this.calNext) {
        this.calNext.addEventListener("click", () => {
          this.calMonth++;
          if (this.calMonth > 11) {
            this.calMonth = 0;
            this.calYear++;
          }
          this.renderCalendar();
        });
      }
      if (this.btnClearDateFilter) {
        this.btnClearDateFilter.addEventListener("click", () => {
          this.selectedDateFilter = null;
          this.btnClearDateFilter.classList.add("hidden");
          this.renderTradesTable();
        });
      }
    }

    async _checkSession() {
      if (!this.token) {
        this.updateHeaderUserUI();
        this.openAuthModal("signin");
        return;
      }
      try {
        const res = await fetch("/api/game/auth/me", {
          headers: { Authorization: `Bearer ${this.token}` },
        });
        if (res.ok) {
          const data = await res.json();
          this.user = data.user;
          localStorage.setItem(this.userKey, JSON.stringify(this.user));
          this.updateHeaderUserUI();
          this.closeAuthModal();
          return;
        }
      } catch (e) {}

      // If offline / token rejected
      this.updateHeaderUserUI();
      if (!this.user) this.openAuthModal("signin");
    }

    _switchAuthTab(tab) {
      if (this.authError) this.authError.classList.add("hidden");
      const isIn = tab === "signin";
      if (this.tabSignIn) this.tabSignIn.classList.toggle("active", isIn);
      if (this.tabSignUp) this.tabSignUp.classList.toggle("active", !isIn);
      if (this.formSignIn) this.formSignIn.classList.toggle("hidden", !isIn);
      if (this.formSignUp) this.formSignUp.classList.toggle("hidden", isIn);
    }

    _showAuthError(msg) {
      if (!this.authError) return;
      this.authError.innerText = msg;
      this.authError.classList.remove("hidden");
    }

    openAuthModal(tab = "signin") {
      this._switchAuthTab(tab);
      if (this.modalAuth) this.modalAuth.classList.remove("hidden");
    }

    closeAuthModal() {
      if (this.modalAuth) this.modalAuth.classList.add("hidden");
    }

    async handleSignIn() {
      const ident = document.getElementById("signin-identifier")?.value.trim() || "";
      const pw = document.getElementById("signin-password")?.value || "";
      if (!ident || !pw) {
        this._showAuthError("Please enter your username/email and password.");
        return;
      }
      try {
        const res = await fetch("/api/game/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ identifier: ident, password: pw }),
        });
        const data = await res.json();
        if (!res.ok) {
          this._showAuthError(data.detail || "Sign in failed.");
          return;
        }
        this._setAuthenticated(data.token, data.user);
      } catch (e) {
        this._showAuthError("Network error during sign in.");
      }
    }

    async handleSignUp() {
      const fullName = document.getElementById("signup-fullname")?.value.trim() || "";
      const username = document.getElementById("signup-username")?.value.trim() || "";
      const email = document.getElementById("signup-email")?.value.trim() || "";
      const pw = document.getElementById("signup-password")?.value || "";
      try {
        const res = await fetch("/api/game/auth/signup", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ full_name: fullName, username, email, password: pw }),
        });
        const data = await res.json();
        if (!res.ok) {
          this._showAuthError(data.detail || "Sign up failed.");
          return;
        }
        this._setAuthenticated(data.token, data.user);
      } catch (e) {
        this._showAuthError("Network error during sign up.");
      }
    }

    _setAuthenticated(token, user) {
      this.token = token;
      this.user = user;
      localStorage.setItem(this.tokenKey, token);
      localStorage.setItem(this.userKey, JSON.stringify(user));
      this.updateHeaderUserUI();
      this.closeAuthModal();
    }

    logout() {
      this.token = null;
      this.user = null;
      localStorage.removeItem(this.tokenKey);
      localStorage.removeItem(this.userKey);
      if (this.modalProfile) this.modalProfile.classList.add("hidden");
      this.updateHeaderUserUI();
      this.openAuthModal("signin");
    }

    updateHeaderUserUI() {
      if (this.lblHeaderUsername) {
        this.lblHeaderUsername.innerText = this.user ? `@${this.user.username}` : "Sign In";
      }
    }

    getAuthHeaders() {
      return this.token ? { Authorization: `Bearer ${this.token}` } : {};
    }

    recordLocalTrade(trade) {
      try {
        const list = JSON.parse(localStorage.getItem(this.historyKey) || "[]");
        list.unshift(trade);
        localStorage.setItem(this.historyKey, JSON.stringify(list.slice(0, 500)));
      } catch (e) {}
    }

    async trackEvent(eventType, metadata = {}) {
      if (!this.token) return;
      try {
        await fetch("/api/game/auth/event", {
          method: "POST",
          headers: { "Content-Type": "application/json", ...this.getAuthHeaders() },
          body: JSON.stringify({ event_type: eventType, metadata }),
        });
      } catch (e) {}
    }

    async openProfileModal() {
      if (!this.modalProfile) return;
      this.modalProfile.classList.remove("hidden");

      const nameEl = document.getElementById("profile-fullname");
      const handleEl = document.getElementById("profile-handle");
      if (nameEl && this.user) nameEl.innerText = this.user.full_name || this.user.username;
      if (handleEl && this.user) handleEl.innerText = `@${this.user.username} • ${this.user.email || ""}`;

      // Fetch server profile + merge local trade history fallback
      let serverData = null;
      if (this.token) {
        try {
          const market = this.app ? this.app.currentMarket : null;
          const res = await fetch(`/api/game/auth/profile${market ? `?market=${market}` : ""}`, {
            headers: this.getAuthHeaders(),
          });
          if (res.ok) serverData = await res.json();
        } catch (e) {}
      }

      const localTrades = (() => {
        try {
          return JSON.parse(localStorage.getItem(this.historyKey) || "[]");
        } catch (e) {
          return [];
        }
      })();

      const trades = (serverData && serverData.trades && serverData.trades.length >= localTrades.length)
        ? serverData.trades
        : localTrades;

      this.profileData = this._computeProfileFromTrades(trades);
      this.selectedDateFilter = null;
      if (this.btnClearDateFilter) this.btnClearDateFilter.classList.add("hidden");

      // Jump calendar to most recent traded month if available
      if (trades.length > 0 && trades[0].session_date) {
        const parts = trades[0].session_date.split("-");
        if (parts.length === 3) {
          this.calYear = parseInt(parts[0], 10);
          this.calMonth = parseInt(parts[1], 10) - 1;
        }
      }

      this.renderProfileStats();
      this.renderCalendar();
      this.renderTradesTable();
    }

    _computeProfileFromTrades(trades) {
      const wins = trades.filter((t) => Number(t.pnl) > 0);
      const losses = trades.filter((t) => Number(t.pnl) < 0);
      const grossWin = wins.reduce((a, t) => a + Number(t.pnl), 0);
      const grossLoss = Math.abs(losses.reduce((a, t) => a + Number(t.pnl), 0));
      const netPnl = Math.round(trades.reduce((a, t) => a + Number(t.pnl), 0) * 100) / 100;
      const winRate = trades.length ? Math.round((wins.length / trades.length) * 1000) / 10 : 0;
      const pf = grossLoss > 0 ? Math.round((grossWin / grossLoss) * 100) / 100 : (grossWin > 0 ? 99.9 : 0);

      const calendar = {};
      for (const t of trades) {
        const d = (t.session_date || "").slice(0, 10);
        if (!d) continue;
        if (!calendar[d]) calendar[d] = { date: d, pnl: 0, trades: 0, wins: 0, losses: 0 };
        calendar[d].pnl = Math.round((calendar[d].pnl + Number(t.pnl)) * 100) / 100;
        calendar[d].trades += 1;
        if (Number(t.pnl) > 0) calendar[d].wins += 1;
        else if (Number(t.pnl) < 0) calendar[d].losses += 1;
      }

      const dayVals = Object.values(calendar).map((c) => c.pnl);
      const bestDay = dayVals.length ? Math.max(...dayVals) : 0;
      const worstDay = dayVals.length ? Math.min(...dayVals) : 0;

      return {
        stats: { total_trades: trades.length, win_rate: winRate, net_pnl: netPnl, profit_factor: pf, best_day: bestDay, worst_day: worstDay },
        calendar,
        trades,
      };
    }

    _fmt(v) {
      return this.app ? this.app.formatCurrency(v) : String(v);
    }

    renderProfileStats() {
      if (!this.profileData) return;
      const s = this.profileData.stats;
      const setTxt = (id, val, cls = null) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.innerText = val;
        if (cls) {
          el.classList.remove("positive", "negative");
          el.classList.add(cls);
        }
      };
      setTxt("prof-net-pnl", `${s.net_pnl >= 0 ? "+" : ""}${this._fmt(s.net_pnl)}`, s.net_pnl >= 0 ? "positive" : "negative");
      setTxt("prof-win-rate", `${s.win_rate}%`);
      setTxt("prof-profit-factor", `${s.profit_factor}`);
      setTxt("prof-total-trades", `${s.total_trades}`);
      setTxt("prof-best-day", `+${this._fmt(Math.max(0, s.best_day))}`, "positive");
      setTxt("prof-worst-day", `${this._fmt(Math.min(0, s.worst_day))}`, "negative");
    }

    renderCalendar() {
      if (!this.calGrid || !this.profileData) return;
      const months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
      if (this.calMonthLabel) {
        this.calMonthLabel.innerText = `${months[this.calMonth]} ${this.calYear}`;
      }

      const firstDay = new Date(this.calYear, this.calMonth, 1);
      const daysInMonth = new Date(this.calYear, this.calMonth + 1, 0).getDate();
      // Monday = 0 ... Sunday = 6
      const startOffset = (firstDay.getDay() + 6) % 7;

      const cells = [];
      for (let i = 0; i < startOffset; i++) {
        cells.push(`<div class="cal-cell cal-empty"></div>`);
      }

      for (let d = 1; d <= daysInMonth; d++) {
        const dateStr = `${this.calYear}-${String(this.calMonth + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
        const rec = this.profileData.calendar[dateStr];
        let cls = "cal-cell";
        let body = `<span class="cal-day-num">${d}</span>`;
        if (rec) {
          cls += rec.pnl > 0 ? " cal-win" : (rec.pnl < 0 ? " cal-loss" : " cal-flat");
          if (this.selectedDateFilter === dateStr) cls += " cal-selected";
          const sign = rec.pnl >= 0 ? "+" : "";
          body += `<span class="cal-day-pnl font-mono">${sign}${this._fmt(rec.pnl)}</span>`;
          body += `<span class="cal-day-trades">${rec.trades}T</span>`;
        }
        cells.push(`<div class="${cls}" data-date="${dateStr}">${body}</div>`);
      }

      this.calGrid.innerHTML = cells.join("");
      this.calGrid.querySelectorAll(".cal-cell[data-date]").forEach((cell) => {
        cell.addEventListener("click", () => {
          const dt = cell.getAttribute("data-date");
          if (!this.profileData.calendar[dt]) return;
          this.selectedDateFilter = dt;
          if (this.btnClearDateFilter) this.btnClearDateFilter.classList.remove("hidden");
          this.renderCalendar();
          this.renderTradesTable();
        });
      });
    }

    renderTradesTable() {
      if (!this.tradesTbody || !this.profileData) return;
      let rows = this.profileData.trades || [];
      if (this.selectedDateFilter) {
        rows = rows.filter((t) => (t.session_date || "").slice(0, 10) === this.selectedDateFilter);
      }

      if (!rows.length) {
        this.tradesTbody.innerHTML = `<tr class="empty-row"><td colspan="8">No recorded trades${this.selectedDateFilter ? ` for ${this.selectedDateFilter}` : ""}.</td></tr>`;
        return;
      }

      this.tradesTbody.innerHTML = rows.slice(0, 100).map((t) => {
        const pnl = Number(t.pnl || 0);
        const cls = pnl >= 0 ? "positive" : "negative";
        return `
          <tr>
            <td class="font-mono">${(t.session_date || "").slice(0, 10)}</td>
            <td><b>${t.symbol}</b></td>
            <td><span class="moneyness-tag ${String(t.side).includes("LONG") || String(t.side).includes("CE") ? "ITM" : "OTM"}">${t.side}</span></td>
            <td class="font-mono">${t.qty}</td>
            <td class="font-mono">${this._fmt(Number(t.entry_price || 0))}</td>
            <td class="font-mono">${this._fmt(Number(t.exit_price || 0))}</td>
            <td>${t.exit_reason}</td>
            <td class="${cls} font-mono"><b>${pnl >= 0 ? "+" : ""}${this._fmt(pnl)}</b></td>
          </tr>
        `;
      }).join("");
    }
  }

  window.AuthProfileManager = AuthProfileManager;
})(window);
