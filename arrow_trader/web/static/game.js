/**
 * ============================================================================
 * ARROW TRADE PRO // Options Battle Simulator Client Engine
 * High-performance TradingView integration, Black-Scholes Greeks,
 * Web Audio Synthesizer & Gamification System.
 * ============================================================================
 */

(function () {
  "use strict";

  // ==========================================================================
  // 1. WEB AUDIO SYNTHESIZER (NO EXTERNAL MP3 DEPENDENCIES)
  // ==========================================================================
  class AudioEngine {
    constructor() {
      this.ctx = null;
      this.enabled = true;
    }

    _init() {
      if (!this.ctx) {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (AudioCtx) this.ctx = new AudioCtx();
      }
      if (this.ctx && this.ctx.state === "suspended") {
        this.ctx.resume();
      }
    }

    playClick() {
      if (!this.enabled) return;
      this._init();
      if (!this.ctx) return;
      try {
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = "sine";
        osc.frequency.setValueAtTime(800, this.ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(300, this.ctx.currentTime + 0.04);
        gain.gain.setValueAtTime(0.08, this.ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.04);
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start();
        osc.stop(this.ctx.currentTime + 0.04);
      } catch (e) {}
    }

    playCandleChime() {
      if (!this.enabled) return;
      this._init();
      if (!this.ctx) return;
      try {
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = "triangle";
        osc.frequency.setValueAtTime(659.25, this.ctx.currentTime); // E5
        gain.gain.setValueAtTime(0.04, this.ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.0001, this.ctx.currentTime + 0.12);
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start();
        osc.stop(this.ctx.currentTime + 0.12);
      } catch (e) {}
    }

    playOrderFilled() {
      if (!this.enabled) return;
      this._init();
      if (!this.ctx) return;
      try {
        const now = this.ctx.currentTime;
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = "sine";
        osc.frequency.setValueAtTime(440, now);
        osc.frequency.exponentialRampToValueAtTime(880, now + 0.12);
        gain.gain.setValueAtTime(0.12, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.18);
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start(now);
        osc.stop(now + 0.18);
      } catch (e) {}
    }

    playTargetWin() {
      if (!this.enabled) return;
      this._init();
      if (!this.ctx) return;
      try {
        const notes = [523.25, 659.25, 783.99, 1046.5]; // C5, E5, G5, C6 (Major arpeggio)
        notes.forEach((freq, idx) => {
          const osc = this.ctx.createOscillator();
          const gain = this.ctx.createGain();
          const start = this.ctx.currentTime + idx * 0.08;
          osc.type = "sine";
          osc.frequency.setValueAtTime(freq, start);
          gain.gain.setValueAtTime(0.15, start);
          gain.gain.exponentialRampToValueAtTime(0.001, start + 0.35);
          osc.connect(gain);
          gain.connect(this.ctx.destination);
          osc.start(start);
          osc.stop(start + 0.35);
        });
      } catch (e) {}
    }

    playStopLossHit() {
      if (!this.enabled) return;
      this._init();
      if (!this.ctx) return;
      try {
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        const now = this.ctx.currentTime;
        osc.type = "sawtooth";
        osc.frequency.setValueAtTime(160, now);
        osc.frequency.linearRampToValueAtTime(110, now + 0.25);
        gain.gain.setValueAtTime(0.12, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start(now);
        osc.stop(now + 0.25);
      } catch (e) {}
    }

    playRoundComplete() {
      if (!this.enabled) return;
      this._init();
      if (!this.ctx) return;
      try {
        const chords = [
          [523.25, 659.25, 783.99], // C major
          [587.33, 739.99, 880.00], // D major
          [659.25, 830.61, 987.77], // E major
        ];
        chords.forEach((chord, cIdx) => {
          const start = this.ctx.currentTime + cIdx * 0.2;
          chord.forEach(freq => {
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = "triangle";
            osc.frequency.setValueAtTime(freq, start);
            gain.gain.setValueAtTime(0.1, start);
            gain.gain.exponentialRampToValueAtTime(0.001, start + 0.45);
            osc.connect(gain);
            gain.connect(this.ctx.destination);
            osc.start(start);
            osc.stop(start + 0.45);
          });
        });
      } catch (e) {}
    }
  }

  // ==========================================================================
  // 2. MATHEMATICAL OPTIONS ENGINE (BLACK-SCHOLES & GREEKS)
  // ==========================================================================
  class OptionsEngine {
    static erf(x) {
      // High-precision polynomial approximation for erf(x)
      const a1 = 0.254829592, a2 = -0.284496736, a3 = 1.421413741;
      const a4 = -1.453152027, a5 = 1.061405429, p = 0.3275911;
      const sign = x < 0 ? -1 : 1;
      const absX = Math.abs(x);
      const t = 1.0 / (1.0 + p * absX);
      const y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * Math.exp(-absX * absX);
      return sign * y;
    }

    static normCdf(x) {
      return 0.5 * (1.0 + this.erf(x / Math.SQRT2));
    }

    static normPdf(x) {
      return Math.exp(-0.5 * x * x) / Math.sqrt(2.0 * Math.PI);
    }

    static calculateTimeToExpiry(barIndex, totalBars = 75, expiryType = "weekly") {
      const barsRemaining = Math.max(1, totalBars - barIndex);
      const frac = barsRemaining / totalBars;
      let days = 2.0 + frac;
      if (expiryType === "next_weekly") days = 7.0 + frac;
      else if (expiryType === "monthly") days = 20.0 + frac;
      return Math.max(0.0005, days / 252.0);
    }

    static price(S, K, T, r = 0.07, iv = 0.15, optionType = "CE") {
      const isCall = optionType.toUpperCase() === "CE";
      const sigma = Math.max(0.01, iv);
      const t = Math.max(0.0001, T);
      const sqrtT = Math.sqrt(t);

      const d1 = (Math.log(S / K) + (r + 0.5 * sigma * sigma) * t) / (sigma * sqrtT);
      const d2 = d1 - sigma * sqrtT;

      let p, delta, thetaAnn;
      if (isCall) {
        p = S * this.normCdf(d1) - K * Math.exp(-r * t) * this.normCdf(d2);
        delta = this.normCdf(d1);
        thetaAnn = (-(S * this.normPdf(d1) * sigma) / (2.0 * sqrtT)) - r * K * Math.exp(-r * t) * this.normCdf(d2);
      } else {
        p = K * Math.exp(-r * t) * this.normCdf(-d2) - S * this.normCdf(-d1);
        delta = this.normCdf(d1) - 1.0;
        thetaAnn = (-(S * this.normPdf(d1) * sigma) / (2.0 * sqrtT)) + r * K * Math.exp(-r * t) * this.normCdf(-d2);
      }

      const gamma = this.normPdf(d1) / (S * sigma * sqrtT);
      const vega = (S * sqrtT * this.normPdf(d1)) / 100.0;
      const thetaDay = thetaAnn / 252.0;

      return {
        price: Math.max(0.05, Math.round(p * 100) / 100),
        delta: Math.round(delta * 1000) / 1000,
        gamma: Math.round(gamma * 100000) / 100000,
        theta: Math.round(thetaDay * 100) / 100,
        vega: Math.round(vega * 100) / 100,
      };
    }

    static barExtremes(candle, strike, T, r = 0.07, iv = 0.15, optionType = "CE") {
      const isCall = optionType.toUpperCase() === "CE";
      const pOpen = this.price(candle.open, strike, T, r, iv, optionType).price;
      const pClose = this.price(candle.close, strike, T, r, iv, optionType).price;
      const pHigh = this.price(isCall ? candle.high : candle.low, strike, T, r, iv, optionType).price;
      const pLow = this.price(isCall ? candle.low : candle.high, strike, T, r, iv, optionType).price;

      return {
        open: pOpen,
        high: Math.max(pOpen, pClose, pHigh),
        low: Math.min(pOpen, pClose, pLow),
        close: pClose
      };
    }
  }

  // ==========================================================================
  // 3. MAIN APP CONTROLLER
  // ==========================================================================
  class GameApp {
    constructor() {
      this.audio = new AudioEngine();

      // State
      this.config = null;
      this.currentMode = "index"; // 'index' or 'stock'
      this.currentSymbol = "NIFTY";
      this.session = null;
      this.currentBarIndex = 0;
      this.isPlaying = false;
      this.replaySpeed = 1000;
      this.timerId = null;
      this.blindMode = false;

      // Account state (Default 10 Lakhs Pro Account)
      this.startingCapital = 1000000.0;
      this.currentCapital = 1000000.0;
      this.dayStartCapital = 1000000.0;
      this.dayPnL = 0.0;
      this.totalTrades = 0;
      this.wins = 0;
      this.losses = 0;
      this.xp = 0;
      this.rank = "Floor Trader";
      this.tradeJournal = [];

      // Trading Order Desk state
      this.instrumentType = "options"; // 'options' or 'futures'
      this.selectedFutDirection = "LONG"; // 'LONG' or 'SHORT'
      this.selectedFutSLPct = 0.5; // 0.5% default SL for futures
      this.selectedFutTargetPct = 1.0; // 1.0% default Target for futures
      this.selectedExpiry = "weekly";
      this.selectedDirection = "CE"; // 'CE' or 'PE'
      this.selectedStrike = null;
      this.selectedLots = 2;
      this.selectedSLPct = 15;
      this.selectedTargetPct = 30;

      // Chart Drawing & Interactive Placing state
      this.fibLines = [];
      this.fibMode = false;
      this.fibStep = 0;
      this.fibAnchor1 = null;
      this.isDraggingFib = false;
      this.lastFibPoints = null;
      this.lastDrawnFibP2 = null;
      this.fibSettings = this.getDefaultFibSettings();
      this.chartPickMode = null; // null | 'SL' | 'TARGET'
      this.previewLines = [];

      // Position Sizing (Risk Management)
      this.sizingMode = "risk"; // 'risk' or 'lots'
      this.selectedRiskPct = 1.0; // 1% default risk
      this.customSLPrice = null;
      this.customTargetPrice = null;

      // Active Position
      this.activePosition = null;

      // Charting
      this.chart = null;
      this.candleSeries = null;
      this.volumeSeries = null;
      this.ema9Series = null;
      this.ema21Series = null;
      this.ema50Series = null;
      this.ma200Series = null;
      this.vwapSeries = null;
      this.supertrendUpSeries = null;
      this.supertrendDownSeries = null;
      this.activePriceLines = [];
      this.chartMarkers = [];

      // Cache for technical indicators computed on session candles
      this.indicatorData = {
        ema9: [],
        ema21: [],
        ema50: [],
        ma200: [],
        vwap: [],
        supertrendUp: [],
        supertrendDown: []
      };

      // Initialize
      this.dom = {};
      this.init();
    }

    async init() {
      this.loadFibSettings();
      this.cacheDomElements();
      this.initChart();
      this.bindEvents();
      this.loadSavedState();
      await this.loadConfig();
      await this.startNewSession();
    }

    cacheDomElements() {
      // Header & Navigation
      this.dom.btnModeIndex = document.getElementById("btn-mode-index");
      this.dom.btnModeStock = document.getElementById("btn-mode-stock");
      this.dom.indexPills = document.getElementById("index-pills");
      this.dom.stockSelectWrapper = document.getElementById("stock-select-wrapper");
      this.dom.stockSelect = document.getElementById("stock-select");
      this.dom.btnRandomStock = document.getElementById("btn-random-stock");
      this.dom.btnNewDay = document.getElementById("btn-new-day");
      this.dom.displayDate = document.getElementById("display-date");
      this.dom.btnToggleBlind = document.getElementById("btn-toggle-blind");
      this.dom.blindIcon = document.getElementById("blind-icon");
      this.dom.blindLabel = document.getElementById("blind-label");
      this.dom.simTime = document.getElementById("sim-time");
      this.dom.barCounter = document.getElementById("bar-counter");

      // HUD
      this.dom.hudBalanceBtn = document.getElementById("hud-balance-btn");
      this.dom.hudCapital = document.getElementById("hud-capital");
      this.dom.hudPnl = document.getElementById("hud-pnl");
      this.dom.hudPnlPct = document.getElementById("hud-pnl-pct");
      this.dom.hudRankBadge = document.getElementById("hud-rank-badge");
      this.dom.hudXpBar = document.getElementById("hud-xp-bar");
      this.dom.btnAudioToggle = document.getElementById("btn-audio-toggle");
      this.dom.audioIcon = document.getElementById("audio-icon");
      this.dom.btnHelpModal = document.getElementById("btn-help-modal");

      // Chart Ticker Bar
      this.dom.tickerSymbol = document.getElementById("ticker-symbol");
      this.dom.tickerBadge = document.getElementById("ticker-badge");
      this.dom.tickerDesc = document.getElementById("ticker-desc");
      this.dom.spotPrice = document.getElementById("spot-price");
      this.dom.spotChange = document.getElementById("spot-change");
      this.dom.barOpen = document.getElementById("bar-open");
      this.dom.barHigh = document.getElementById("bar-high");
      this.dom.barLow = document.getElementById("bar-low");
      this.dom.barClose = document.getElementById("bar-close");
      this.dom.barVol = document.getElementById("bar-vol");
      this.dom.chartWrapper = document.getElementById("chart-wrapper");
      this.dom.tvChart = document.getElementById("tv-chart");
      this.dom.tradeChartOverlay = document.getElementById("trade-chart-overlay");

      // Chart Drawing & Interactive Placing Tools
      this.dom.btnFitChart = document.getElementById("btn-fit-chart");
      this.dom.btnDrawFib = document.getElementById("btn-draw-fib");
      this.dom.btnFibSettings = document.getElementById("btn-fib-settings");
      this.dom.btnAutoFib = document.getElementById("btn-auto-fib");
      this.dom.btnClearFib = document.getElementById("btn-clear-fib");
      this.dom.btnChartPickTarget = document.getElementById("btn-chart-pick-target");
      this.dom.btnChartPickSL = document.getElementById("btn-chart-pick-sl");
      this.dom.chartActionBanner = document.getElementById("chart-action-banner");
      this.dom.chartActionText = document.getElementById("chart-action-text");
      this.dom.btnCancelChartAction = document.getElementById("btn-cancel-chart-action");

      // Indicators
      this.dom.toggleEma9 = document.getElementById("toggle-ema9");
      this.dom.toggleEma21 = document.getElementById("toggle-ema21");
      this.dom.toggleEma50 = document.getElementById("toggle-ema50");
      this.dom.toggleMa200 = document.getElementById("toggle-ma200");
      this.dom.toggleVwap = document.getElementById("toggle-vwap");
      this.dom.toggleSupertrend = document.getElementById("toggle-supertrend");

      // Replay Deck
      this.dom.btnReplayRestart = document.getElementById("btn-replay-restart");
      this.dom.btnReplayPlay = document.getElementById("btn-replay-play");
      this.dom.playIcon = document.getElementById("play-icon");
      this.dom.playText = document.getElementById("play-text");
      this.dom.btnReplayStep = document.getElementById("btn-replay-step");
      this.dom.timelineSlider = document.getElementById("timeline-slider");

      // Active Position Deck
      this.dom.positionDeck = document.getElementById("position-deck");
      this.dom.posSymbolTag = document.getElementById("pos-symbol-tag");
      this.dom.btnExitPosition = document.getElementById("btn-exit-position");
      this.dom.posLivePnl = document.getElementById("pos-live-pnl");
      this.dom.posLiveRoi = document.getElementById("pos-live-roi");
      this.dom.posCapitalDeployed = document.getElementById("pos-capital-deployed");
      this.dom.posSlVal = document.getElementById("pos-sl-val");
      this.dom.posCurVal = document.getElementById("pos-cur-val");
      this.dom.posTgVal = document.getElementById("pos-tg-val");
      this.dom.meterFill = document.getElementById("meter-fill");
      this.dom.meterMarker = document.getElementById("meter-marker");
      this.dom.btnSlBreakeven = document.getElementById("btn-sl-breakeven");
      this.dom.btnTrailSl = document.getElementById("btn-trail-sl");

      // Order Desk Header & Instrument Selectors
      this.dom.deskTitle = document.getElementById("desk-title");
      this.dom.deskSubtitle = document.getElementById("desk-subtitle");
      this.dom.btnInstOptions = document.getElementById("btn-inst-options");
      this.dom.btnInstFutures = document.getElementById("btn-inst-futures");
      this.dom.optionsSpecificControls = document.getElementById("options-specific-controls");
      this.dom.futuresSpecificControls = document.getElementById("futures-specific-controls");
      this.dom.btnFutLong = document.getElementById("btn-fut-long");
      this.dom.btnFutShort = document.getElementById("btn-fut-short");
      this.dom.futContractName = document.getElementById("fut-contract-name");
      this.dom.futLtp = document.getElementById("fut-ltp");
      this.dom.futMarginPerLot = document.getElementById("fut-margin-per-lot");
      this.dom.futNotionalVal = document.getElementById("fut-notional-val");
      this.dom.summaryPriceLabel = document.getElementById("summary-price-label");
      this.dom.summaryCapitalLabel = document.getElementById("summary-capital-label");
      this.dom.summaryDeltaLabel = document.getElementById("summary-delta-label");

      this.dom.badgeLotSize = document.getElementById("badge-lot-size");
      this.dom.btnOptCall = document.getElementById("btn-opt-call");
      this.dom.btnOptPut = document.getElementById("btn-opt-put");
      this.dom.strikeStepLabel = document.getElementById("strike-step-label");
      this.dom.strikeMatrixTable = document.getElementById("strike-matrix-table");

      // Position Sizing & Lots Calculator
      this.dom.btnSizingRisk = document.getElementById("btn-sizing-risk");
      this.dom.btnSizingLots = document.getElementById("btn-sizing-lots");
      this.dom.boxRiskSizing = document.getElementById("box-risk-sizing");
      this.dom.boxManualLots = document.getElementById("box-manual-lots");
      this.dom.riskAmountReadout = document.getElementById("risk-amount-readout");
      this.dom.inputCustomRisk = document.getElementById("input-custom-risk");
      this.dom.calcMaxLoss = document.getElementById("calc-max-loss");
      this.dom.calcLotsResult = document.getElementById("calc-lots-result");
      this.dom.calcRiskPerLot = document.getElementById("calc-risk-per-lot");

      this.dom.totalQtyReadout = document.getElementById("total-qty-readout");
      this.dom.inputLots = document.getElementById("input-lots");
      this.dom.btnLotMax = document.getElementById("btn-lot-max");

      // Manual & Preset SL / Target
      this.dom.btnChartSLQuick = document.getElementById("btn-chart-sl-quick");
      this.dom.btnChartTargetQuick = document.getElementById("btn-chart-target-quick");
      this.dom.inputSLPrice = document.getElementById("input-sl-price");
      this.dom.inputTargetPrice = document.getElementById("input-target-price");
      this.dom.slReadout = document.getElementById("sl-readout");
      this.dom.targetReadout = document.getElementById("target-readout");
      this.dom.rrRatio = document.getElementById("rr-ratio");
      this.dom.summaryPremium = document.getElementById("summary-premium");
      this.dom.summaryTotalCost = document.getElementById("summary-total-cost");
      this.dom.summaryDelta = document.getElementById("summary-delta");
      this.dom.btnExecuteOrder = document.getElementById("btn-execute-order");
      this.dom.btnExecuteText = document.getElementById("btn-execute-text");

      // Drawer & Journal
      this.dom.drawerToggleBtn = document.getElementById("drawer-toggle-btn");
      this.dom.appFooterDrawer = document.querySelector(".app-footer-drawer");
      this.dom.journalTradeCount = document.getElementById("journal-trade-count");
      this.dom.journalWinrate = document.getElementById("journal-winrate");
      this.dom.journalTotalPnl = document.getElementById("journal-total-pnl");
      this.dom.journalTbody = document.getElementById("journal-tbody");

      // Modals
      this.dom.modalEod = document.getElementById("modal-eod");
      this.dom.modalSettings = document.getElementById("modal-settings");
      this.dom.modalHelp = document.getElementById("modal-help");
      this.dom.btnCloseSettings = document.getElementById("btn-close-settings");
      this.dom.btnCloseHelp = document.getElementById("btn-close-help");
      this.dom.btnSaveCapital = document.getElementById("btn-save-capital");
      this.dom.btnCancelSettings = document.getElementById("btn-cancel-settings");
      this.dom.inputCustomCapital = document.getElementById("input-custom-capital");
      this.dom.btnEodNextDay = document.getElementById("btn-eod-next-day");
      this.dom.btnEodReplayDay = document.getElementById("btn-eod-replay-day");
      this.dom.btnEodClose = document.getElementById("btn-eod-close");
      this.dom.btnGotIt = document.getElementById("btn-gotIt") || document.getElementById("btn-got-it");

      // Fib Settings Modal
      this.dom.modalFibSettings = document.getElementById("modal-fib-settings");
      this.dom.btnCloseFibSettings = document.getElementById("btn-close-fib-settings");
      this.dom.btnCancelFibSettings = document.getElementById("btn-cancel-fib-settings");
      this.dom.btnSaveFibSettings = document.getElementById("btn-save-fib-settings");
      this.dom.btnResetFibDefaults = document.getElementById("btn-reset-fib-defaults");
      this.dom.btnFibAddLevel = document.getElementById("btn-fib-add-level");
      this.dom.fibLevelsList = document.getElementById("fib-levels-list");
      this.dom.fibOptPrices = document.getElementById("fib-opt-prices");
      this.dom.fibOptLabels = document.getElementById("fib-opt-labels");
    }

    loadSavedState() {
      try {
        const saved = localStorage.getItem("arrow_game_state");
        if (saved) {
          const s = JSON.parse(saved);
          if (s.startingCapital) {
            this.startingCapital = parseFloat(s.startingCapital) || 1000000.0;
          }
          if (typeof s.currentCapital === "number") {
            this.currentCapital = parseFloat(s.currentCapital);
          } else {
            this.currentCapital = this.startingCapital;
          }
          if (typeof s.dayStartCapital === "number") {
            this.dayStartCapital = parseFloat(s.dayStartCapital);
          } else {
            this.dayStartCapital = this.currentCapital;
          }
          if (s.xp) this.xp = s.xp;
          if (s.rank) this.rank = s.rank;
          if (typeof s.audioEnabled === "boolean") {
            this.audio.enabled = s.audioEnabled;
            this.updateAudioButtonState();
          }
        }
      } catch (e) {}
      this.dayStartCapital = this.currentCapital;
      this.updateHUD();
    }

    saveState() {
      try {
        const state = {
          startingCapital: this.startingCapital,
          currentCapital: this.currentCapital,
          dayStartCapital: this.dayStartCapital,
          xp: this.xp,
          rank: this.rank,
          audioEnabled: this.audio.enabled
        };
        localStorage.setItem("arrow_game_state", JSON.stringify(state));
      } catch (e) {}
    }

    async loadConfig() {
      try {
        const res = await fetch("/api/game/config");
        if (res.ok) {
          this.config = await res.json();
          if (this.config.state) {
            const st = this.config.state;
            const hasLocal = localStorage.getItem("arrow_game_state");
            if (!hasLocal) {
              if (st.starting_balance) this.startingCapital = st.starting_balance;
              if (st.current_balance) this.currentCapital = st.current_balance;
              this.dayStartCapital = this.currentCapital;
            }
            if (st.xp) this.xp = st.xp || this.xp;
            if (st.rank) this.rank = st.rank || this.rank;
            this.updateHUD();
          }
        }
      } catch (e) {
        console.warn("Local config load fallback:", e);
      }
    }

    initChart() {
      if (!window.LightweightCharts) {
        console.error("LightweightCharts library not loaded");
        return;
      }

      this.chart = LightweightCharts.createChart(this.dom.tvChart, {
        layout: {
          background: { color: "#080b10" },
          textColor: "#94a3b8",
          fontFamily: "'JetBrains Mono', 'Inter', sans-serif",
          fontSize: 11,
        },
        grid: {
          vertLines: { color: "rgba(255, 255, 255, 0.04)" },
          horzLines: { color: "rgba(255, 255, 255, 0.04)" },
        },
        crosshair: {
          mode: LightweightCharts.CrosshairMode.Normal,
          vertLine: { color: "#38bdf8", width: 1, style: 3 },
          horzLine: { color: "#38bdf8", width: 1, style: 3 },
        },
        timeScale: {
          borderColor: "rgba(255, 255, 255, 0.08)",
          timeVisible: true,
          secondsVisible: false,
          shiftVisibleRangeOnNewBar: true,
          rightOffset: 12,
          barSpacing: 10,
          minBarSpacing: 3,
        },
        rightPriceScale: {
          borderColor: "rgba(255, 255, 255, 0.08)",
          scaleMargins: { top: 0.12, bottom: 0.28 },
          autoScale: true,
        },
        handleScale: {
          axisPressedMouseMove: { time: true, price: true },
          axisDoubleClickReset: { time: true, price: true },
          mouseWheel: true,
          pinch: true,
        },
        handleScroll: {
          mouseWheel: true,
          pressedMouseMove: true,
          horzTouchDrag: true,
          vertTouchDrag: true,
        },
      });

      // Candlestick Series
      this.candleSeries = this.chart.addCandlestickSeries({
        upColor: "#10b981",
        downColor: "#f43f5e",
        borderUpColor: "#10b981",
        borderDownColor: "#f43f5e",
        wickUpColor: "#10b981",
        wickDownColor: "#f43f5e",
        priceFormat: {
          type: "price",
          precision: 2,
          minMove: 0.05,
        },
      });

      // Volume Series
      this.volumeSeries = this.chart.addHistogramSeries({
        color: "rgba(56, 189, 248, 0.35)",
        priceFormat: { type: "volume" },
        priceScaleId: "", // overlay scale
        scaleMargins: { top: 0.8, bottom: 0 },
      });

      // Overlays
      this.ema9Series = this.chart.addLineSeries({
        color: "#38bdf8",
        lineWidth: 1.5,
        title: "EMA 9",
        lastValueVisible: false,
        priceLineVisible: false,
      });

      this.ema21Series = this.chart.addLineSeries({
        color: "#f59e0b",
        lineWidth: 1.5,
        title: "EMA 21",
        lastValueVisible: false,
        priceLineVisible: false,
      });

      this.ema50Series = this.chart.addLineSeries({
        color: "#a855f7",
        lineWidth: 1.5,
        title: "EMA 50",
        lastValueVisible: false,
        priceLineVisible: false,
      });

      this.ma200Series = this.chart.addLineSeries({
        color: "#f97316",
        lineWidth: 2,
        title: "200 MA",
        lastValueVisible: false,
        priceLineVisible: false,
      });

      this.vwapSeries = this.chart.addLineSeries({
        color: "#8b5cf6",
        lineWidth: 1.5,
        title: "VWAP",
        lastValueVisible: false,
        priceLineVisible: false,
      });

      // Supertrend (Bull: Emerald Green, Bear: Crimson Red)
      this.supertrendUpSeries = this.chart.addLineSeries({
        color: "#10b981",
        lineWidth: 2,
        title: "Supertrend (Bull)",
        lastValueVisible: false,
        priceLineVisible: false,
      });

      this.supertrendDownSeries = this.chart.addLineSeries({
        color: "#f43f5e",
        lineWidth: 2,
        title: "Supertrend (Bear)",
        lastValueVisible: false,
        priceLineVisible: false,
      });

      // Auto resize handling (Window + ResizeObserver)
      const updateChartDimensions = () => {
        if (this.chart && this.dom.chartWrapper) {
          const w = this.dom.chartWrapper.clientWidth;
          const h = this.dom.chartWrapper.clientHeight;
          if (w > 50 && h > 50) {
            this.chart.applyOptions({ width: w, height: h });
          }
        }
      };

      window.addEventListener("resize", updateChartDimensions);
      if (window.ResizeObserver && this.dom.chartWrapper) {
        const ro = new ResizeObserver(() => updateChartDimensions());
        ro.observe(this.dom.chartWrapper);
      }
      setTimeout(updateChartDimensions, 100);

      // Mouse & Touch Drag Support for interactive on-screen Fibonacci Drawing
      const getChartPointPrice = (e) => {
        if (!this.candleSeries || !this.dom.tvChart) return null;
        const rect = this.dom.tvChart.getBoundingClientRect();
        const clientY = (e.touches && e.touches[0]) ? e.touches[0].clientY : e.clientY;
        if (typeof clientY !== "number") return null;
        const y = clientY - rect.top;
        if (y < 0 || y > rect.height) return null;
        const p = this.candleSeries.coordinateToPrice(y);
        return (p != null && !isNaN(p) && p > 0) ? p : null;
      };

      const onPointerDown = (e) => {
        if (!this.fibMode) return;
        const price = getChartPointPrice(e);
        if (!price) return;
        this.isDraggingFib = true;
        this.fibDragStartPrice = price;
        this.fibAnchor1 = price;
        this.fibStep = 2;
        // Temporarily disable chart pan so mouse drag draws Fibonacci cleanly
        this.chart.applyOptions({
          handleScroll: { mouseWheel: false, pressedMouseMove: false, horzTouchDrag: false, vertTouchDrag: false }
        });
        this.drawFibRetracement(this.fibAnchor1, price);
        this.dom.chartActionText.innerText = `📐 Dragging Fib from ₹${this.fibAnchor1.toFixed(1)}... Release to place.`;
      };

      const onPointerMove = (e) => {
        if (!this.fibMode) return;
        if (this.isDraggingFib || this.fibStep === 2) {
          const price = getChartPointPrice(e);
          if (price && this.fibAnchor1) {
            this.drawFibRetracement(this.fibAnchor1, price);
            const status = this.isDraggingFib ? "Release to place" : "Click to place";
            this.dom.chartActionText.innerText = `📐 Fib: ₹${this.fibAnchor1.toFixed(1)} → ₹${price.toFixed(1)} (${status})`;
          }
        }
      };

      const onPointerUp = (e) => {
        if (!this.fibMode) return;
        if (this.isDraggingFib) {
          this.chart.applyOptions({
            handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: true }
          });
          this.isDraggingFib = false;
          const price = getChartPointPrice(e) || this.lastDrawnFibP2;
          if (price && this.fibAnchor1 && Math.abs(price - this.fibAnchor1) > 0.5) {
            this.lastFibPoints = { p1: this.fibAnchor1, p2: price };
            this.drawFibRetracement(this.fibAnchor1, price);
            this.cancelChartAction();
            this.audio.playClick();
          }
        }
      };

      if (this.dom.tvChart) {
        this.dom.tvChart.addEventListener("mousedown", onPointerDown);
        this.dom.tvChart.addEventListener("touchstart", onPointerDown, { passive: true });
      }
      window.addEventListener("mousemove", onPointerMove);
      window.addEventListener("mouseup", onPointerUp);
      window.addEventListener("touchmove", onPointerMove, { passive: true });
      window.addEventListener("touchend", onPointerUp, { passive: true });

      // Interactive Chart Click Handler for Fibonacci & SL/Target placement
      this.chart.subscribeClick((param) => {
        this.handleChartClick(param);
      });
    }

    // ========================================================================
    // SESSION MANAGEMENT
    // ========================================================================
    async startNewSession(symbol = null, date = null) {
      this.pause();
      this.activePosition = null;
      this.dom.positionDeck.classList.add("hidden");
      this.dom.tradeChartOverlay.classList.add("hidden");
      this.clearPriceLines();
      this.clearPreviewLines();
      this.clearFib();
      this.cancelChartAction();
      this.customSLPrice = null;
      this.customTargetPrice = null;
      this.dayStartCapital = this.currentCapital;
      this.dayPnL = 0.0;
      this.tradeJournal = [];
      this.renderJournal();
      this.updateHUD();
      this.saveState();

      // Clear all chart series immediately to eliminate old price ranges
      if (this.candleSeries) this.candleSeries.setData([]);
      if (this.volumeSeries) this.volumeSeries.setData([]);
      if (this.ema9Series) this.ema9Series.setData([]);
      if (this.ema21Series) this.ema21Series.setData([]);
      if (this.ema50Series) this.ema50Series.setData([]);
      if (this.ma200Series) this.ma200Series.setData([]);
      if (this.vwapSeries) this.vwapSeries.setData([]);
      if (this.supertrendUpSeries) this.supertrendUpSeries.setData([]);
      if (this.supertrendDownSeries) this.supertrendDownSeries.setData([]);

      const sym = symbol || this.currentSymbol;

      // Show loading UI
      this.dom.spotPrice.innerText = "Loading...";
      this.dom.strikeMatrixTable.innerHTML = `<div class="table-loading font-mono">Loading ${sym} Historical Data...</div>`;

      try {
        const res = await fetch("/api/game/session", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            mode: this.currentMode,
            symbol: sym,
            date: date,
            blind_mode: this.blindMode
          })
        });

        if (!res.ok) {
          throw new Error(await res.text());
        }

        const data = await res.json();
        this.session = data.session;
        this.currentSymbol = this.session.symbol;
        this.currentBarIndex = 0;

        // Compute technical indicators for entire session
        this.computeTechnicalIndicators(this.session.candles);

        // Update UI
        this.updateHeaderAndInfo();
        this.resetReplayToStart();
        this.audio.playClick();
      } catch (err) {
        console.error("Session creation error:", err);
        alert("Failed to start session: " + err.message);
      }
    }

    computeTechnicalIndicators(candles) {
      if (!candles || !candles.length) return;

      const closes = candles.map(c => c.close);

      // EMA calculation helper
      const ema = (period, values) => {
        const k = 2 / (period + 1);
        const res = [];
        let val = values[0];
        res.push(val);
        for (let i = 1; i < values.length; i++) {
          val = values[i] * k + val * (1 - k);
          res.push(val);
        }
        return res;
      };

      // SMA with cumulative warmup
      const sma = (period, values) => {
        const res = [];
        let sum = 0;
        for (let i = 0; i < values.length; i++) {
          sum += values[i];
          if (i < period) {
            res.push(sum / (i + 1));
          } else {
            sum -= values[i - period];
            res.push(sum / period);
          }
        }
        return res;
      };

      const ema9Vals = ema(9, closes);
      const ema21Vals = ema(21, closes);
      const ema50Vals = ema(50, closes);
      const ma200Vals = sma(200, closes);

      // VWAP = sum(typical_price * volume) / sum(volume)
      let cumVol = 0;
      let cumTypicalVol = 0;
      const vwapVals = [];
      candles.forEach(c => {
        const typical = (c.high + c.low + c.close) / 3.0;
        const vol = c.volume || 1;
        cumVol += vol;
        cumTypicalVol += (typical * vol);
        vwapVals.push(cumVol > 0 ? (cumTypicalVol / cumVol) : c.close);
      });

      // Supertrend (ATR 10, Multiplier 3.0)
      const n = candles.length;
      const tr = [];
      for (let i = 0; i < n; i++) {
        const h = candles[i].high;
        const l = candles[i].low;
        const prevClose = i > 0 ? candles[i - 1].close : candles[i].open;
        const trVal = Math.max(h - l, Math.abs(h - prevClose), Math.abs(l - prevClose));
        tr.push(trVal);
      }

      const atrPeriod = 10;
      const mult = 3.0;
      const atr = [];
      let sumTr = 0;
      for (let i = 0; i < Math.min(atrPeriod, n); i++) {
        sumTr += tr[i];
        atr.push(sumTr / (i + 1));
      }
      for (let i = atrPeriod; i < n; i++) {
        const curAtr = (atr[i - 1] * (atrPeriod - 1) + tr[i]) / atrPeriod;
        atr.push(curAtr);
      }

      let prevFinalUp = 0;
      let prevFinalDown = 0;
      let trend = 1;
      const supertrendUp = [];
      const supertrendDown = [];

      for (let i = 0; i < n; i++) {
        const bar = candles[i];
        const hl2 = (bar.high + bar.low) / 2.0;
        const curAtr = atr[i] || (bar.high - bar.low);
        const basicUp = hl2 + mult * curAtr;
        const basicDown = hl2 - mult * curAtr;

        let finalUp = basicUp;
        let finalDown = basicDown;

        if (i > 0) {
          finalUp = (basicUp < prevFinalUp || candles[i - 1].close > prevFinalUp) ? basicUp : prevFinalUp;
          finalDown = (basicDown > prevFinalDown || candles[i - 1].close < prevFinalDown) ? basicDown : prevFinalDown;
        }

        let curTrend = trend;
        if (trend === 1) {
          if (bar.close < finalDown) {
            curTrend = -1;
          } else {
            curTrend = 1;
          }
        } else {
          if (bar.close > finalUp) {
            curTrend = 1;
          } else {
            curTrend = -1;
          }
        }

        const stVal = curTrend === 1 ? finalDown : finalUp;
        const roundVal = Math.round(stVal * 100) / 100;

        if (curTrend === 1) {
          supertrendUp.push({ time: bar.time, value: roundVal });
          supertrendDown.push({ time: bar.time });
        } else {
          supertrendDown.push({ time: bar.time, value: roundVal });
          supertrendUp.push({ time: bar.time });
        }

        trend = curTrend;
        prevFinalUp = finalUp;
        prevFinalDown = finalDown;
      }

      this.indicatorData.ema9 = candles.map((c, i) => ({ time: c.time, value: Math.round(ema9Vals[i] * 100) / 100 }));
      this.indicatorData.ema21 = candles.map((c, i) => ({ time: c.time, value: Math.round(ema21Vals[i] * 100) / 100 }));
      this.indicatorData.ema50 = candles.map((c, i) => ({ time: c.time, value: Math.round(ema50Vals[i] * 100) / 100 }));
      this.indicatorData.ma200 = candles.map((c, i) => ({ time: c.time, value: Math.round(ma200Vals[i] * 100) / 100 }));
      this.indicatorData.vwap = candles.map((c, i) => ({ time: c.time, value: Math.round(vwapVals[i] * 100) / 100 }));
      this.indicatorData.supertrendUp = supertrendUp;
      this.indicatorData.supertrendDown = supertrendDown;
    }

    updateHeaderAndInfo() {
      if (!this.session) return;

      // Symbol & Badges
      const isBlind = this.blindMode;
      this.dom.tickerSymbol.innerText = isBlind ? "MYSTERY ASSET" : this.session.symbol;
      this.dom.tickerBadge.innerText = isBlind ? "SECRET INSTRUMENT" : this.session.badge;
      this.dom.tickerDesc.innerText = isBlind ? "Price Action Challenge (Blind Mode Active)" : this.session.description;

      // Date Display
      if (isBlind) {
        this.dom.displayDate.innerText = `Mystery Day #${(this.session.date || "142").replace(/-/g, "") % 999}`;
      } else {
        this.dom.displayDate.innerText = this.session.pretty_date || this.session.date;
      }

      // Lot Size
      this.dom.badgeLotSize.innerHTML = `Lot: <b>${this.session.lot_size} Qty</b>`;
      this.dom.strikeStepLabel.innerText = `Step: ${this.session.strike_step} pts`;

      // Slider Max
      this.dom.timelineSlider.max = Math.max(0, this.session.total_bars - 1);
    }

    resetChartViewport(forceFullDay = true) {
      if (!this.chart || !this.candleSeries) return;

      const apply = () => {
        try {
          // 1. Force Price Scale to autoScale mode so candles fit vertically
          this.chart.priceScale("right").applyOptions({
            autoScale: true,
            scaleMargins: { top: 0.12, bottom: 0.28 },
          });

          if (this.candleSeries.priceScale) {
            this.candleSeries.priceScale().applyOptions({
              autoScale: true,
            });
          }

          // 2. Set Price Format precision based on instrument
          const tickSize = this.session?.tick_size || 0.05;
          this.candleSeries.applyOptions({
            priceFormat: {
              type: "price",
              precision: 2,
              minMove: tickSize,
            },
          });

          // 3. Reset Time Scale internal zoom & pan
          this.chart.timeScale().resetTimeScale();

          // 4. Set optimal Visible Logical Range
          const totalBars = this.session?.total_bars || 75;
          if (forceFullDay || this.currentBarIndex <= 5) {
            this.chart.timeScale().setVisibleLogicalRange({
              from: -3,
              to: Math.min(85, Math.max(35, totalBars + 5)),
            });
          } else {
            const fromBar = Math.max(-3, this.currentBarIndex - 45);
            const toBar = this.currentBarIndex + 15;
            this.chart.timeScale().setVisibleLogicalRange({
              from: fromBar,
              to: toBar,
            });
          }
        } catch (err) {
          console.warn("Chart viewport reset warning:", err);
        }
      };

      apply();
      requestAnimationFrame(apply);
    }

    resetReplayToStart() {
      this.currentBarIndex = 0;
      this.dom.timelineSlider.value = 0;
      this.chartMarkers = [];

      this.clearPriceLines();
      this.clearPreviewLines();
      this.clearFib();

      // Render the opening 09:15 bar
      this.renderCurrentChartState();

      // Force viewport reset to perfectly frame the new day and instrument
      this.resetChartViewport(true);
    }

    renderCurrentChartState() {
      if (!this.session || !this.session.candles.length) return;

      const visibleBars = this.session.candles.slice(0, this.currentBarIndex + 1);
      const currentCandle = visibleBars[visibleBars.length - 1];

      // Format for TradingView
      const formattedBars = visibleBars.map(c => ({
        time: c.time,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }));

      const formattedVols = visibleBars.map(c => ({
        time: c.time,
        value: c.volume || 100,
        color: c.close >= c.open ? "rgba(16, 185, 129, 0.35)" : "rgba(244, 63, 94, 0.35)",
      }));

      this.candleSeries.setData(formattedBars);
      this.volumeSeries.setData(formattedVols);

      // Overlays: only set data for active indicators, explicitly clear inactive ones
      const endIndex = this.currentBarIndex + 1;

      if (this.dom.toggleEma9 && this.dom.toggleEma9.classList.contains("active")) {
        this.ema9Series.setData(this.indicatorData.ema9.slice(0, endIndex));
      } else if (this.ema9Series) {
        this.ema9Series.setData([]);
      }

      if (this.dom.toggleEma21 && this.dom.toggleEma21.classList.contains("active")) {
        this.ema21Series.setData(this.indicatorData.ema21.slice(0, endIndex));
      } else if (this.ema21Series) {
        this.ema21Series.setData([]);
      }

      if (this.dom.toggleEma50 && this.dom.toggleEma50.classList.contains("active")) {
        this.ema50Series.setData(this.indicatorData.ema50.slice(0, endIndex));
      } else if (this.ema50Series) {
        this.ema50Series.setData([]);
      }

      if (this.dom.toggleMa200 && this.dom.toggleMa200.classList.contains("active")) {
        this.ma200Series.setData(this.indicatorData.ma200.slice(0, endIndex));
      } else if (this.ma200Series) {
        this.ma200Series.setData([]);
      }

      if (this.dom.toggleVwap && this.dom.toggleVwap.classList.contains("active")) {
        this.vwapSeries.setData(this.indicatorData.vwap.slice(0, endIndex));
      } else if (this.vwapSeries) {
        this.vwapSeries.setData([]);
      }

      if (this.dom.toggleSupertrend && this.dom.toggleSupertrend.classList.contains("active")) {
        this.supertrendUpSeries.setData(this.indicatorData.supertrendUp.slice(0, endIndex));
        this.supertrendDownSeries.setData(this.indicatorData.supertrendDown.slice(0, endIndex));
      } else {
        if (this.supertrendUpSeries) this.supertrendUpSeries.setData([]);
        if (this.supertrendDownSeries) this.supertrendDownSeries.setData([]);
      }

      this.candleSeries.setMarkers(this.chartMarkers);

      // Auto-tracking: keep current candle visible on chart as replay advances or jumps
      if (this.currentBarIndex > 0) {
        try {
          const logicalRange = this.chart.timeScale().getVisibleLogicalRange();
          if (logicalRange) {
            const span = Math.max(25, logicalRange.to - logicalRange.from);
            if (this.currentBarIndex >= logicalRange.to - 2) {
              this.chart.timeScale().setVisibleLogicalRange({
                from: this.currentBarIndex - span + 8,
                to: this.currentBarIndex + 8,
              });
            } else if (this.currentBarIndex < logicalRange.from) {
              this.chart.timeScale().setVisibleLogicalRange({
                from: Math.max(-3, this.currentBarIndex - 3),
                to: Math.max(-3, this.currentBarIndex - 3) + span,
              });
            }
          }
        } catch (e) {}
      } else {
        // At opening bar (Bar 0), ensure chart view is auto-fitted
        this.resetChartViewport(true);
      }

      // Update Tickers & OHLC
      const dayOpen = this.session.candles[0].open;
      const netPts = currentCandle.close - dayOpen;
      const netPct = (netPts / dayOpen) * 100;

      this.dom.spotPrice.innerText = `₹ ${currentCandle.close.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
      this.dom.spotChange.innerText = `${netPts >= 0 ? "+" : ""}${netPts.toFixed(2)} (${netPct.toFixed(2)}%)`;
      this.dom.spotChange.className = `spot-change font-mono ${netPts >= 0 ? "positive" : "negative"}`;

      this.dom.barOpen.innerText = currentCandle.open.toFixed(2);
      this.dom.barHigh.innerText = currentCandle.high.toFixed(2);
      this.dom.barLow.innerText = currentCandle.low.toFixed(2);
      this.dom.barClose.innerText = currentCandle.close.toFixed(2);
      this.dom.barVol.innerText = (currentCandle.volume || 0).toLocaleString("en-IN");

      // Sim Time & Bar Index
      this.dom.simTime.innerText = `${currentCandle.time_str || "09:15"} AM`;
      this.dom.barCounter.innerText = `Bar ${this.currentBarIndex + 1} / ${this.session.total_bars}`;
      this.dom.timelineSlider.value = this.currentBarIndex;

      // Update Option Chain matrix around current spot
      this.renderStrikeMatrix(currentCandle.close);

      // Evaluate Active Position if open
      if (this.activePosition) {
        this.evaluatePositionStep(currentCandle);
      }
    }

    // ========================================================================
    // REPLAY CONTROLS (PLAY, PAUSE, STEP, SPEED)
    // ========================================================================
    togglePlay() {
      if (this.isPlaying) {
        this.pause();
      } else {
        this.play();
      }
    }

    play() {
      if (!this.session) return;
      if (this.currentBarIndex >= this.session.total_bars - 1) {
        // At end, restart or alert
        this.restartDay();
      }
      this.isPlaying = true;
      this.dom.btnReplayPlay.classList.add("is-playing");
      this.dom.playIcon.innerText = "⏸";
      this.dom.playText.innerText = "PAUSE";
      this.audio.playClick();

      this.timerId = setInterval(() => {
        this.stepNextBar(true);
      }, this.replaySpeed);
    }

    pause() {
      this.isPlaying = false;
      if (this.timerId) {
        clearInterval(this.timerId);
        this.timerId = null;
      }
      this.dom.btnReplayPlay.classList.remove("is-playing");
      this.dom.playIcon.innerText = "▶";
      this.dom.playText.innerText = "PLAY";
    }

    stepNextBar(fromTimer = false) {
      if (!this.session) return;
      if (this.currentBarIndex < this.session.total_bars - 1) {
        this.currentBarIndex++;
        this.renderCurrentChartState();
        if (!fromTimer) this.audio.playCandleChime();
      } else {
        // Completed 75th bar (15:30 EOD)
        this.pause();
        this.audio.playRoundComplete();
        this.onEndOfDayReached();
      }
    }

    restartDay() {
      this.pause();
      this.audio.playClick();
      this.activePosition = null;
      this.dom.positionDeck.classList.add("hidden");
      this.dom.tradeChartOverlay.classList.add("hidden");
      this.clearPriceLines();
      this.clearPreviewLines();
      this.currentCapital = (typeof this.dayStartCapital === "number") ? this.dayStartCapital : this.currentCapital;
      this.dayPnL = 0;
      this.tradeJournal = [];
      this.renderJournal();
      this.updateHUD();
      this.saveState();
      this.resetReplayToStart();
    }

    jumpToBar(idx) {
      if (!this.session) return;
      this.currentBarIndex = Math.max(0, Math.min(this.session.total_bars - 1, parseInt(idx)));
      this.renderCurrentChartState();
    }

    setSpeed(ms) {
      this.replaySpeed = parseInt(ms);
      if (this.isPlaying) {
        this.pause();
        this.play();
      }
    }

    // ========================================================================
    // STRIKE MATRIX & OPTIONS PRICING
    // ========================================================================
    renderStrikeMatrix(spotPrice) {
      if (!this.session) return;

      const step = this.session.strike_step;
      const lot = this.session.lot_size;
      const iv = this.session.default_iv || 0.16;
      const T = OptionsEngine.calculateTimeToExpiry(
        this.currentBarIndex,
        this.session.total_bars,
        this.selectedExpiry
      );

      const atmStrike = Math.round(spotPrice / step) * step;

      // If user hasn't selected strike yet, default to ATM
      if (!this.selectedStrike) {
        this.selectedStrike = atmStrike;
      }

      // 7 Strikes: ATM, +/- 3 steps
      const offsets = [-3, -2, -1, 0, 1, 2, 3];
      const rows = offsets.map(off => {
        const k = atmStrike + (off * step);
        const isATM = (off === 0);
        const isSelected = (this.selectedStrike === k);

        const ce = OptionsEngine.price(spotPrice, k, T, 0.07, iv, "CE");
        const pe = OptionsEngine.price(spotPrice, k, T, 0.07, iv, "PE");

        const isCall = this.selectedDirection === "CE";
        const optData = isCall ? ce : pe;

        // Moneyness tag
        let moneyness = "ATM";
        if (isCall) {
          moneyness = off === 0 ? "ATM" : (off < 0 ? `ITM ${Math.abs(off)}` : `OTM ${off}`);
        } else {
          moneyness = off === 0 ? "ATM" : (off > 0 ? `ITM ${off}` : `OTM ${Math.abs(off)}`);
        }

        const tagClass = off === 0 ? "ATM" : ((isCall && off < 0) || (!isCall && off > 0) ? "ITM" : "OTM");
        const lotCost = Math.round(optData.price * lot);

        return `
          <div class="strike-row ${isATM ? "is-atm" : ""} ${isSelected ? "selected" : ""}" data-strike="${k}">
            <div class="strike-cell-left">
              <span class="strike-num font-mono">${k}</span>
              <span class="moneyness-tag ${tagClass}">${moneyness}</span>
            </div>
            <div class="strike-cell-right">
              <span class="strike-premium font-mono">₹ ${optData.price.toFixed(2)}</span>
              <span class="strike-meta font-mono">Δ ${optData.delta.toFixed(2)} | ₹${lotCost.toLocaleString("en-IN")}/lot</span>
            </div>
          </div>
        `;
      });

      this.dom.strikeMatrixTable.innerHTML = rows.join("");

      // Bind row clicks
      this.dom.strikeMatrixTable.querySelectorAll(".strike-row").forEach(el => {
        el.addEventListener("click", () => {
          this.selectedStrike = parseFloat(el.getAttribute("data-strike"));
          this.audio.playClick();
          this.renderStrikeMatrix(spotPrice);
          this.updateOrderSummary();
        });
      });

      this.updateOrderSummary();
    }

    switchInstrumentType(type) {
      if (this.activePosition) {
        alert("You have an active open position! Close it before switching instrument desks.");
        return;
      }
      this.instrumentType = type;
      this.customSLPrice = null;
      this.customTargetPrice = null;
      this.clearPreviewLines();

      if (type === "futures") {
        this.dom.btnInstFutures.classList.add("active");
        this.dom.btnInstOptions.classList.remove("active");
        this.dom.futuresSpecificControls.classList.remove("hidden");
        this.dom.optionsSpecificControls.classList.add("hidden");
        this.dom.deskTitle.innerText = "FUTURES ORDER DESK";
        this.dom.deskSubtitle.innerText = "Intraday Futures Margin & Direct Spot Pricing";
        this.dom.summaryPriceLabel.innerText = "FUT PRICE";
        this.dom.summaryCapitalLabel.innerText = "MARGIN REQ";
        this.dom.summaryDeltaLabel.innerText = "LEVERAGE";

        // Update SL & Target preset chips for Futures (percentage of spot)
        const slValues = ["0.3", "0.5", "1.0", "1.5"];
        document.querySelectorAll(".preset-chips .preset-chip[data-sl]").forEach((btn, idx) => {
          if (slValues[idx]) {
            btn.setAttribute("data-sl", slValues[idx]);
            btn.innerText = `${slValues[idx]}%`;
            btn.classList.toggle("active", slValues[idx] === "0.5");
          }
        });
        const targetValues = ["0.5", "1.0", "2.0", "3.0"];
        document.querySelectorAll(".preset-chips .preset-chip[data-target]").forEach((btn, idx) => {
          if (targetValues[idx]) {
            btn.setAttribute("data-target", targetValues[idx]);
            btn.innerText = `${targetValues[idx]}%`;
            btn.classList.toggle("active", targetValues[idx] === "1.0");
          }
        });
      } else {
        this.dom.btnInstOptions.classList.add("active");
        this.dom.btnInstFutures.classList.remove("active");
        this.dom.optionsSpecificControls.classList.remove("hidden");
        this.dom.futuresSpecificControls.classList.add("hidden");
        this.dom.deskTitle.innerText = "OPTIONS ORDER DESK";
        this.dom.deskSubtitle.innerText = "Black-Scholes Simulated Live Greeks";
        this.dom.summaryPriceLabel.innerText = "PREMIUM";
        this.dom.summaryCapitalLabel.innerText = "TOTAL CAPITAL";
        this.dom.summaryDeltaLabel.innerText = "EST. DELTA";

        // Restore SL & Target preset chips for Options (percentage of premium)
        const slValues = ["10", "15", "25", "35"];
        document.querySelectorAll(".preset-chips .preset-chip[data-sl]").forEach((btn, idx) => {
          if (slValues[idx]) {
            btn.setAttribute("data-sl", slValues[idx]);
            btn.innerText = `${slValues[idx]}%`;
            btn.classList.toggle("active", slValues[idx] === "15");
          }
        });
        const targetValues = ["20", "30", "50", "100"];
        document.querySelectorAll(".preset-chips .preset-chip[data-target]").forEach((btn, idx) => {
          if (targetValues[idx]) {
            btn.setAttribute("data-target", targetValues[idx]);
            btn.innerText = `${targetValues[idx]}%`;
            btn.classList.toggle("active", targetValues[idx] === "30");
          }
        });
      }

      this.updateOrderSummary();
    }

    setFuturesDirection(dir) {
      this.selectedFutDirection = dir; // 'LONG' or 'SHORT'
      if (dir === "LONG") {
        this.dom.btnFutLong.classList.add("active", "glow-green");
        this.dom.btnFutShort.classList.remove("active");
      } else {
        this.dom.btnFutShort.classList.add("active");
        this.dom.btnFutLong.classList.remove("active", "glow-green");
      }
      this.customSLPrice = null;
      this.customTargetPrice = null;
      this.audio.playClick();
      this.updateOrderSummary();
    }

    updateOrderSummary() {
      if (this.instrumentType === "futures") {
        this.updateFuturesOrderSummary();
      } else {
        this.updateOptionsOrderSummary();
      }
    }

    updateFuturesOrderSummary() {
      if (!this.session) return;
      const candle = this.session.candles[this.currentBarIndex];
      const spot = candle.close;
      const lot = this.session.lot_size;
      const isLong = this.selectedFutDirection === "LONG";

      // Margin Rate (~12.5% for Index, ~15% for Stocks)
      const marginRate = (this.session.instrument_type === "stock" || this.currentMode === "stock") ? 0.15 : 0.125;
      const leverage = (1 / marginRate).toFixed(1) + "x";
      const notionalPerLot = Math.round(spot * lot);
      const marginPerLot = Math.round(notionalPerLot * marginRate);

      // Contract details in DOM
      if (this.dom.futContractName) this.dom.futContractName.innerText = `${this.session.symbol} FUT`;
      if (this.dom.futLtp) this.dom.futLtp.innerText = `₹ ${spot.toFixed(2)}`;
      if (this.dom.futMarginPerLot) this.dom.futMarginPerLot.innerText = `₹ ${marginPerLot.toLocaleString("en-IN")}`;
      if (this.dom.futNotionalVal) this.dom.futNotionalVal.innerText = `₹ ${notionalPerLot.toLocaleString("en-IN")}`;

      // 1. Determine Stop Loss Price
      let slPrice;
      if (this.customSLPrice != null) {
        slPrice = this.customSLPrice;
        if (isLong && slPrice >= spot) {
          slPrice = Math.round(spot * (1 - this.selectedFutSLPct / 100) * 100) / 100;
          this.customSLPrice = slPrice;
        } else if (!isLong && slPrice <= spot) {
          slPrice = Math.round(spot * (1 + this.selectedFutSLPct / 100) * 100) / 100;
          this.customSLPrice = slPrice;
        }
        const slDiffPct = Math.max(0.1, Math.abs(spot - slPrice) / spot * 100);
        this.dom.slReadout.innerText = `Custom -${slDiffPct.toFixed(1)}% (₹${slPrice.toFixed(2)})`;
      } else {
        slPrice = isLong
          ? Math.round(spot * (1 - this.selectedFutSLPct / 100) * 100) / 100
          : Math.round(spot * (1 + this.selectedFutSLPct / 100) * 100) / 100;
        this.dom.slReadout.innerText = `-${this.selectedFutSLPct}% (₹${slPrice.toFixed(2)})`;
        if (this.dom.inputSLPrice !== document.activeElement) {
          this.dom.inputSLPrice.value = slPrice.toFixed(2);
        }
      }

      // 2. Determine Target Price
      let targetPrice;
      if (this.customTargetPrice != null) {
        targetPrice = this.customTargetPrice;
        if (isLong && targetPrice <= spot) {
          targetPrice = Math.round(spot * (1 + this.selectedFutTargetPct / 100) * 100) / 100;
          this.customTargetPrice = targetPrice;
        } else if (!isLong && targetPrice >= spot) {
          targetPrice = Math.round(spot * (1 - this.selectedFutTargetPct / 100) * 100) / 100;
          this.customTargetPrice = targetPrice;
        }
        const tgDiffPct = Math.max(0.1, Math.abs(targetPrice - spot) / spot * 100);
        this.dom.targetReadout.innerText = `Custom +${tgDiffPct.toFixed(1)}% (₹${targetPrice.toFixed(2)})`;
      } else {
        targetPrice = isLong
          ? Math.round(spot * (1 + this.selectedFutTargetPct / 100) * 100) / 100
          : Math.round(spot * (1 - this.selectedFutTargetPct / 100) * 100) / 100;
        this.dom.targetReadout.innerText = `+${this.selectedFutTargetPct}% (₹${targetPrice.toFixed(2)})`;
        if (this.dom.inputTargetPrice !== document.activeElement) {
          this.dom.inputTargetPrice.value = targetPrice.toFixed(2);
        }
      }

      // 3. Risk-Based Position Sizing (Lots Calculator)
      const accountEquity = Math.max(10000, this.currentCapital + (this.activePosition ? this.activePosition.pnl : 0));
      const maxRiskRupees = Math.round(accountEquity * (this.selectedRiskPct / 100));
      const pointsRisk = Math.max(0.5, Math.abs(spot - slPrice));
      const pointsReward = Math.max(0.5, Math.abs(targetPrice - spot));
      const riskPerLot = Math.round(pointsRisk * lot * 100) / 100;

      let lots;
      if (this.sizingMode === "risk") {
        const autoLots = riskPerLot > 0 ? Math.max(1, Math.floor(maxRiskRupees / riskPerLot)) : 1;
        const maxAffordable = marginPerLot > 0 ? Math.max(1, Math.floor(this.currentCapital / marginPerLot)) : 100;
        lots = Math.max(1, Math.min(autoLots, maxAffordable));
        this.selectedLots = lots;
        this.dom.inputLots.value = lots;
      } else {
        lots = parseInt(this.selectedLots) || 1;
      }

      const totalQty = lots * lot;
      const totalMargin = lots * marginPerLot;
      const totalRisk = Math.round(pointsRisk * totalQty);
      const totalReward = Math.round(pointsReward * totalQty);
      const rr = totalRisk > 0 ? (totalReward / totalRisk).toFixed(1) : "2.0";

      // 4. Update DOM Readouts
      this.dom.riskAmountReadout.innerText = `₹ ${maxRiskRupees.toLocaleString("en-IN")} (${this.selectedRiskPct}%)`;
      this.dom.calcMaxLoss.innerText = `₹ ${maxRiskRupees.toLocaleString("en-IN")}`;
      this.dom.calcLotsResult.innerText = `${lots} Lots (${totalQty} Qty)`;
      this.dom.calcRiskPerLot.innerText = `₹ ${riskPerLot.toLocaleString("en-IN")}`;
      this.dom.totalQtyReadout.innerText = `${totalQty} Qty (${lots} Lots)`;
      this.dom.rrRatio.innerText = `1 : ${rr}`;

      this.dom.summaryPremium.innerText = `₹ ${spot.toFixed(2)}`;
      this.dom.summaryTotalCost.innerText = `₹ ${totalMargin.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
      this.dom.summaryDelta.innerText = `${leverage} (1.00 Δ)`;

      const actionVerb = isLong ? "BUY" : "SHORT";
      this.dom.btnExecuteText.innerText = `${actionVerb} ${lots} LOTS ${this.session.symbol} FUT (Margin: ₹${totalMargin.toLocaleString("en-IN")})`;
      this.dom.btnExecuteOrder.className = `btn-execute ${isLong ? "glow-call" : "glow-put"}`;

      // 5. Visual Preview lines on chart
      this.updatePreviewLines(targetPrice, slPrice);
    }

    updateOptionsOrderSummary() {
      if (!this.session) return;

      const spot = this.session.candles[this.currentBarIndex].close;
      const step = this.session.strike_step;
      const lot = this.session.lot_size;
      const iv = this.session.default_iv || 0.16;
      const T = OptionsEngine.calculateTimeToExpiry(this.currentBarIndex, this.session.total_bars, this.selectedExpiry);

      if (!this.selectedStrike) {
        this.selectedStrike = Math.round(spot / step) * step;
      }

      const opt = OptionsEngine.price(spot, this.selectedStrike, T, 0.07, iv, this.selectedDirection);

      // 1. Determine Stop Loss Price (from manual/chart input or preset %)
      let slPrice;
      if (this.customSLPrice != null) {
        slPrice = Math.max(0.05, this.customSLPrice);
        if (slPrice >= opt.price) {
          slPrice = Math.max(0.05, Math.round(opt.price * 0.85 * 100) / 100);
          this.customSLPrice = slPrice;
        }
        const slDiffPct = Math.max(1, Math.round(((opt.price - slPrice) / opt.price) * 100));
        this.dom.slReadout.innerText = `Custom -${slDiffPct}% (₹${slPrice.toFixed(2)})`;
      } else {
        slPrice = Math.max(0.05, Math.round(opt.price * (1 - this.selectedSLPct / 100) * 100) / 100);
        this.dom.slReadout.innerText = `-${this.selectedSLPct}% (₹${slPrice.toFixed(2)})`;
        if (this.dom.inputSLPrice !== document.activeElement) {
          this.dom.inputSLPrice.value = slPrice.toFixed(2);
        }
      }

      // 2. Determine Target Price (from manual/chart input or preset %)
      let targetPrice;
      if (this.customTargetPrice != null) {
        targetPrice = Math.max(opt.price + 0.1, this.customTargetPrice);
        const targetDiffPct = Math.max(1, Math.round(((targetPrice - opt.price) / opt.price) * 100));
        this.dom.targetReadout.innerText = `Custom +${targetDiffPct}% (₹${targetPrice.toFixed(2)})`;
      } else {
        targetPrice = Math.round(opt.price * (1 + this.selectedTargetPct / 100) * 100) / 100;
        this.dom.targetReadout.innerText = `+${this.selectedTargetPct}% (₹${targetPrice.toFixed(2)})`;
        if (this.dom.inputTargetPrice !== document.activeElement) {
          this.dom.inputTargetPrice.value = targetPrice.toFixed(2);
        }
      }

      // 3. Risk-Based Position Sizing (Lots Calculator)
      const accountEquity = Math.max(10000, this.currentCapital + (this.activePosition ? (this.activePosition.currentPrice * this.activePosition.qty) : 0));
      const maxRiskRupees = Math.round(accountEquity * (this.selectedRiskPct / 100));

      const lossPerShare = Math.max(0.5, Math.round((opt.price - slPrice) * 100) / 100);
      const riskPerLot = Math.round(lossPerShare * lot * 100) / 100;

      let lots;
      if (this.sizingMode === "risk") {
        const autoLots = riskPerLot > 0 ? Math.max(1, Math.floor(maxRiskRupees / riskPerLot)) : 1;
        const costPerLot = Math.round(opt.price * lot * 100) / 100;
        const maxAffordable = costPerLot > 0 ? Math.max(1, Math.floor(this.currentCapital / costPerLot)) : 100;
        lots = Math.max(1, Math.min(autoLots, maxAffordable));
        this.selectedLots = lots;
        this.dom.inputLots.value = lots;
      } else {
        lots = parseInt(this.selectedLots) || 1;
      }

      const totalQty = lots * lot;
      const totalCost = Math.round(opt.price * totalQty * 100) / 100;
      const totalRisk = Math.round(lossPerShare * totalQty);
      const totalReward = Math.round(Math.max(0, targetPrice - opt.price) * totalQty);
      const rr = totalRisk > 0 ? (totalReward / totalRisk).toFixed(1) : "2.0";

      // 4. Update DOM Readouts
      this.dom.riskAmountReadout.innerText = `₹ ${maxRiskRupees.toLocaleString("en-IN")} (${this.selectedRiskPct}%)`;
      this.dom.calcMaxLoss.innerText = `₹ ${maxRiskRupees.toLocaleString("en-IN")}`;
      this.dom.calcLotsResult.innerText = `${lots} Lots (${totalQty} Qty)`;
      this.dom.calcRiskPerLot.innerText = `₹ ${riskPerLot.toLocaleString("en-IN")}`;

      this.dom.totalQtyReadout.innerText = `${totalQty} Qty (${lots} Lots)`;
      this.dom.rrRatio.innerText = `1 : ${rr}`;

      this.dom.summaryPremium.innerText = `₹ ${opt.price.toFixed(2)}`;
      this.dom.summaryTotalCost.innerText = `₹ ${totalCost.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
      this.dom.summaryDelta.innerText = `${opt.delta.toFixed(2)} Δ`;

      this.dom.btnExecuteText.innerText = `BUY ${lots} LOTS ${this.selectedStrike} ${this.selectedDirection} (₹${totalCost.toLocaleString("en-IN")})`;
      this.dom.btnExecuteOrder.className = `btn-execute ${this.selectedDirection === "CE" ? "glow-call" : "glow-put"}`;

      // 5. Update Visual Preview lines on the chart (before trade execution)
      const delta = Math.max(0.15, Math.abs(opt.delta));
      const isCall = this.selectedDirection === "CE";
      const targetSpot = isCall ? (spot + (targetPrice - opt.price) / delta) : (spot - (targetPrice - opt.price) / delta);
      const slSpot = isCall ? (spot - (opt.price - slPrice) / delta) : (spot + (opt.price - slPrice) / delta);
      this.updatePreviewLines(targetSpot, slSpot);
    }

    // ========================================================================
    // ORDER EXECUTION & POSITION SIMULATION
    // ========================================================================
    executeOrder() {
      if (this.instrumentType === "futures") {
        this.executeFuturesOrder();
      } else {
        this.executeOptionsOrder();
      }
    }

    executeFuturesOrder() {
      if (!this.session) return;
      if (this.activePosition) {
        alert("You already have an active open position! Square off or let it hit target/stop loss before placing another trade.");
        return;
      }

      const candle = this.session.candles[this.currentBarIndex];
      const spot = candle.close;
      const lot = this.session.lot_size;
      const isLong = this.selectedFutDirection === "LONG";
      const marginRate = (this.session.instrument_type === "stock" || this.currentMode === "stock") ? 0.15 : 0.125;
      const marginPerLot = Math.round(spot * lot * marginRate);
      const lots = parseInt(this.selectedLots) || 1;
      const totalQty = lots * lot;
      const totalMargin = lots * marginPerLot;

      if (totalMargin > this.currentCapital) {
        alert(`Insufficient Capital for Futures Margin! Required Margin: ₹${totalMargin.toLocaleString("en-IN")}, Available Cash: ₹${this.currentCapital.toLocaleString("en-IN")}`);
        return;
      }

      // Stop Loss & Target
      let slPrice = this.customSLPrice != null
        ? this.customSLPrice
        : (isLong ? Math.round(spot * (1 - this.selectedFutSLPct / 100) * 100) / 100 : Math.round(spot * (1 + this.selectedFutSLPct / 100) * 100) / 100);

      let targetPrice = this.customTargetPrice != null
        ? this.customTargetPrice
        : (isLong ? Math.round(spot * (1 + this.selectedFutTargetPct / 100) * 100) / 100 : Math.round(spot * (1 - this.selectedFutTargetPct / 100) * 100) / 100);

      // Logical bounds check
      if (isLong && slPrice >= spot) slPrice = Math.round(spot * 0.995 * 100) / 100;
      if (!isLong && slPrice <= spot) slPrice = Math.round(spot * 1.005 * 100) / 100;
      if (isLong && targetPrice <= spot) targetPrice = Math.round(spot * 1.01 * 100) / 100;
      if (!isLong && targetPrice >= spot) targetPrice = Math.round(spot * 0.99 * 100) / 100;

      const slPct = Math.round(Math.abs(spot - slPrice) / spot * 1000) / 10;
      const targetPct = Math.round(Math.abs(targetPrice - spot) / spot * 1000) / 10;

      // Deduct margin from available capital
      this.currentCapital = Math.round((this.currentCapital - totalMargin) * 100) / 100;
      this.clearPreviewLines();

      this.activePosition = {
        id: "TF-" + Date.now().toString(36),
        instrumentType: "futures",
        symbol: this.session.symbol,
        strike: 0,
        direction: this.selectedFutDirection, // 'LONG' or 'SHORT'
        expiry: "monthly",
        lots: lots,
        lotSize: lot,
        qty: totalQty,
        entryPrice: spot,
        currentPrice: spot,
        slPrice: slPrice,
        targetPrice: targetPrice,
        initialSLPct: slPct,
        initialTargetPct: targetPct,
        totalCost: totalMargin,
        marginBlocked: totalMargin,
        entryBar: this.currentBarIndex,
        entryTime: candle.time_str || "09:15",
        entrySpot: spot,
        pnl: 0,
        roiPct: 0
      };

      this.audio.playOrderFilled();
      this.drawPositionChartLines();
      this.updateHUD();
      this.saveState();

      // Add Entry Marker on Chart
      this.chartMarkers.push({
        time: candle.time,
        position: isLong ? "belowBar" : "aboveBar",
        color: isLong ? "#10b981" : "#f43f5e",
        shape: isLong ? "arrowUp" : "arrowDown",
        text: `${isLong ? "BUY" : "SHORT"} ${this.session.symbol} FUT @ ₹${spot.toFixed(1)}`,
      });
      this.candleSeries.setMarkers(this.chartMarkers);

      this.renderActivePositionDeck();
    }

    executeOptionsOrder() {
      if (!this.session) return;
      if (this.activePosition) {
        alert("You already have an active open position! Square off or let it hit target/stop loss before placing another bet.");
        return;
      }

      const candle = this.session.candles[this.currentBarIndex];
      const spot = candle.close;
      const lot = this.session.lot_size;
      const iv = this.session.default_iv || 0.16;
      const T = OptionsEngine.calculateTimeToExpiry(this.currentBarIndex, this.session.total_bars, this.selectedExpiry);

      const opt = OptionsEngine.price(spot, this.selectedStrike, T, 0.07, iv, this.selectedDirection);
      const lots = parseInt(this.selectedLots) || 1;
      const totalQty = lots * lot;
      const totalCost = Math.round(opt.price * totalQty * 100) / 100;

      // Balance check
      if (totalCost > this.currentCapital) {
        alert(`Insufficient Funds! Required: ₹${totalCost.toLocaleString("en-IN")}, Available Cash: ₹${this.currentCapital.toLocaleString("en-IN")}`);
        return;
      }

      // Compute SL and Target prices
      let slPrice = this.customSLPrice != null
        ? Math.max(0.05, this.customSLPrice)
        : Math.max(0.05, Math.round(opt.price * (1 - this.selectedSLPct / 100) * 100) / 100);

      let targetPrice = this.customTargetPrice != null
        ? Math.max(opt.price + 0.1, this.customTargetPrice)
        : Math.round(opt.price * (1 + this.selectedTargetPct / 100) * 100) / 100;

      if (slPrice >= opt.price) {
        slPrice = Math.max(0.05, Math.round(opt.price * 0.85 * 100) / 100);
      }

      const slPct = Math.max(1, Math.round(((opt.price - slPrice) / opt.price) * 100));
      const targetPct = Math.max(1, Math.round(((targetPrice - opt.price) / opt.price) * 100));

      // Deduct deployed capital from available cash
      this.currentCapital = Math.round((this.currentCapital - totalCost) * 100) / 100;
      this.clearPreviewLines();

      this.activePosition = {
        id: "T-" + Date.now().toString(36),
        instrumentType: "options",
        symbol: this.session.symbol,
        strike: this.selectedStrike,
        direction: this.selectedDirection,
        expiry: this.selectedExpiry,
        lots: lots,
        lotSize: lot,
        qty: totalQty,
        entryPrice: opt.price,
        currentPrice: opt.price,
        slPrice: slPrice,
        targetPrice: targetPrice,
        initialSLPct: slPct,
        initialTargetPct: targetPct,
        totalCost: totalCost,
        entryBar: this.currentBarIndex,
        entryTime: candle.time_str || "09:15",
        entrySpot: spot,
        pnl: 0,
        roiPct: 0
      };

      // Sound & Chart
      this.audio.playOrderFilled();
      this.drawPositionChartLines();
      this.updateHUD();
      this.saveState();

      // Add Entry Marker on Chart
      this.chartMarkers.push({
        time: candle.time,
        position: this.selectedDirection === "CE" ? "belowBar" : "aboveBar",
        color: this.selectedDirection === "CE" ? "#10b981" : "#f43f5e",
        shape: this.selectedDirection === "CE" ? "arrowUp" : "arrowDown",
        text: `BUY ${this.selectedStrike} ${this.selectedDirection} @ ₹${opt.price.toFixed(1)}`,
      });
      this.candleSeries.setMarkers(this.chartMarkers);

      // Render Active Position Deck
      this.renderActivePositionDeck();
    }

    drawPositionChartLines() {
      this.clearPriceLines();
      if (!this.activePosition) return;

      const pos = this.activePosition;

      // FUTURES POSITION CHART LINES (Direct Spot Pricing)
      if (pos.instrumentType === "futures") {
        const entryLine = this.candleSeries.createPriceLine({
          price: pos.entryPrice,
          color: "#38bdf8",
          lineWidth: 1.5,
          lineStyle: 0, // Solid
          axisLabelVisible: true,
          title: `ENTRY: ${pos.symbol} FUT ${pos.direction} (₹${pos.entryPrice.toFixed(1)})`,
        });

        const targetLine = this.candleSeries.createPriceLine({
          price: pos.targetPrice,
          color: "#10b981",
          lineWidth: 1.5,
          lineStyle: 2, // Dashed
          axisLabelVisible: true,
          title: `TARGET (₹${pos.targetPrice.toFixed(1)})`,
        });

        const slLine = this.candleSeries.createPriceLine({
          price: pos.slPrice,
          color: "#f43f5e",
          lineWidth: 1.5,
          lineStyle: 2, // Dashed
          axisLabelVisible: true,
          title: `STOP LOSS (₹${pos.slPrice.toFixed(1)})`,
        });

        this.activePriceLines = [entryLine, targetLine, slLine];
        return;
      }

      // OPTIONS POSITION CHART LINES (Spot Translation)
      const spot = this.activePosition.entrySpot;
      const isCall = this.activePosition.direction === "CE";
      const delta = Math.abs(0.5); // delta translation to underlying spot points
      const targetMovePts = ((this.activePosition.targetPrice - this.activePosition.entryPrice) / delta);
      const slMovePts = ((this.activePosition.entryPrice - this.activePosition.slPrice) / delta);

      const targetSpot = isCall ? (spot + targetMovePts) : (spot - targetMovePts);
      const slSpot = isCall ? (spot - slMovePts) : (spot + slMovePts);

      const entryLine = this.candleSeries.createPriceLine({
        price: spot,
        color: "#38bdf8",
        lineWidth: 1.5,
        lineStyle: 0, // Solid
        axisLabelVisible: true,
        title: `ENTRY: ${this.activePosition.strike} ${this.activePosition.direction}`,
      });

      const targetLine = this.candleSeries.createPriceLine({
        price: targetSpot,
        color: "#10b981",
        lineWidth: 1.5,
        lineStyle: 2, // Dashed
        axisLabelVisible: true,
        title: `TARGET (+${this.activePosition.initialTargetPct}%)`,
      });

      const slLine = this.candleSeries.createPriceLine({
        price: slSpot,
        color: "#f43f5e",
        lineWidth: 1.5,
        lineStyle: 2, // Dashed
        axisLabelVisible: true,
        title: `STOP LOSS (-${this.activePosition.initialSLPct}%)`,
      });

      this.activePriceLines = [entryLine, targetLine, slLine];
    }

    clearPriceLines() {
      if (this.activePriceLines && this.candleSeries) {
        this.activePriceLines.forEach(l => {
          try { this.candleSeries.removePriceLine(l); } catch (e) {}
        });
      }
      this.activePriceLines = [];
    }

    // ========================================================================
    // CHART PREVIEW LINES (PLANNING SL / TARGET)
    // ========================================================================
    updatePreviewLines(targetSpot, slSpot) {
      this.clearPreviewLines();
      if (this.activePosition || !this.candleSeries) return;

      const tLine = this.candleSeries.createPriceLine({
        price: targetSpot,
        color: "rgba(16, 185, 129, 0.75)",
        lineWidth: 1,
        lineStyle: 2, // Dashed
        axisLabelVisible: true,
        title: `PLAN TARGET (₹${targetSpot.toFixed(1)})`
      });

      const slLine = this.candleSeries.createPriceLine({
        price: slSpot,
        color: "rgba(244, 63, 94, 0.75)",
        lineWidth: 1,
        lineStyle: 2, // Dashed
        axisLabelVisible: true,
        title: `PLAN SL (₹${slSpot.toFixed(1)})`
      });

      this.previewLines = [tLine, slLine];
    }

    clearPreviewLines() {
      if (this.previewLines && this.candleSeries) {
        this.previewLines.forEach(l => {
          try { this.candleSeries.removePriceLine(l); } catch (e) {}
        });
      }
      this.previewLines = [];
    }

    // ========================================================================
    // FIBONACCI RETRACEMENT & INTERACTIVE CHART PLACEMENT
    // ========================================================================
    getDefaultFibSettings() {
      return {
        showPrices: true,
        showLabels: true,
        levels: [
          { ratio: 0.0, label: "0.0%", color: "#94a3b8", width: 1, style: 2, enabled: true },
          { ratio: 0.236, label: "23.6%", color: "#38bdf8", width: 1, style: 2, enabled: true },
          { ratio: 0.382, label: "38.2%", color: "#f59e0b", width: 1, style: 2, enabled: true },
          { ratio: 0.500, label: "50.0% (Eq)", color: "#ec4899", width: 1.5, style: 0, enabled: true },
          { ratio: 0.618, label: "61.8% (Golden)", color: "#10b981", width: 2, style: 0, enabled: true },
          { ratio: 0.786, label: "78.6%", color: "#a855f7", width: 1, style: 2, enabled: true },
          { ratio: 1.000, label: "100.0%", color: "#94a3b8", width: 1, style: 2, enabled: true },
          { ratio: 1.272, label: "127.2%", color: "#3b82f6", width: 1, style: 2, enabled: false },
          { ratio: 1.618, label: "161.8% (Ext)", color: "#06b6d4", width: 1.5, style: 2, enabled: true },
          { ratio: 2.618, label: "261.8%", color: "#eab308", width: 1, style: 2, enabled: false }
        ]
      };
    }

    loadFibSettings() {
      try {
        const saved = localStorage.getItem("arrow_fib_settings");
        if (saved) {
          const parsed = JSON.parse(saved);
          if (parsed && Array.isArray(parsed.levels) && parsed.levels.length > 0) {
            this.fibSettings = parsed;
            return;
          }
        }
      } catch (e) {}
      this.fibSettings = this.getDefaultFibSettings();
    }

    saveFibSettings() {
      try {
        localStorage.setItem("arrow_fib_settings", JSON.stringify(this.fibSettings));
      } catch (e) {}
    }

    openFibSettingsModal() {
      this.renderFibSettingsList();
      if (this.dom.fibOptPrices) {
        this.dom.fibOptPrices.checked = this.fibSettings.showPrices !== false;
      }
      if (this.dom.fibOptLabels) {
        this.dom.fibOptLabels.checked = this.fibSettings.showLabels !== false;
      }
      if (this.dom.modalFibSettings) {
        this.dom.modalFibSettings.classList.remove("hidden");
      }
      this.audio.playClick();
    }

    renderFibSettingsList() {
      if (!this.dom.fibLevelsList) return;
      const levels = this.fibSettings.levels;
      this.dom.fibLevelsList.innerHTML = levels.map((lvl, idx) => {
        return `
          <div class="fib-level-row" data-idx="${idx}">
            <div style="text-align:center;">
              <input type="checkbox" class="fib-row-enabled" ${lvl.enabled !== false ? "checked" : ""}>
            </div>
            <div>
              <input type="number" step="0.001" class="fib-input-ratio" value="${lvl.ratio}">
            </div>
            <div>
              <input type="text" class="fib-input-label" value="${lvl.label || ""}">
            </div>
            <div style="text-align:center;">
              <input type="color" class="fib-input-color" value="${lvl.color || "#38bdf8"}">
            </div>
            <div>
              <select class="fib-select-style">
                <option value="0" ${lvl.style === 0 ? "selected" : ""}>Solid</option>
                <option value="2" ${lvl.style === 2 ? "selected" : ""}>Dashed</option>
                <option value="1" ${lvl.style === 1 ? "selected" : ""}>Dotted</option>
              </select>
            </div>
            <div style="text-align:center;">
              <button class="fib-btn-del" title="Remove level">✕</button>
            </div>
          </div>
        `;
      }).join("");

      // Bind row inputs
      this.dom.fibLevelsList.querySelectorAll(".fib-level-row").forEach(row => {
        const idx = parseInt(row.getAttribute("data-idx"));
        const chk = row.querySelector(".fib-row-enabled");
        const ratioInp = row.querySelector(".fib-input-ratio");
        const labelInp = row.querySelector(".fib-input-label");
        const colorInp = row.querySelector(".fib-input-color");
        const styleSel = row.querySelector(".fib-select-style");
        const delBtn = row.querySelector(".fib-btn-del");

        if (chk) chk.addEventListener("change", (e) => { levels[idx].enabled = e.target.checked; });
        if (ratioInp) ratioInp.addEventListener("input", (e) => {
          const val = parseFloat(e.target.value);
          if (!isNaN(val)) levels[idx].ratio = val;
        });
        if (labelInp) labelInp.addEventListener("input", (e) => { levels[idx].label = e.target.value; });
        if (colorInp) colorInp.addEventListener("input", (e) => { levels[idx].color = e.target.value; });
        if (styleSel) styleSel.addEventListener("change", (e) => { levels[idx].style = parseInt(e.target.value); });
        if (delBtn) delBtn.addEventListener("click", () => {
          levels.splice(idx, 1);
          this.renderFibSettingsList();
        });
      });
    }

    applyFibPreset(presetName) {
      if (presetName === "tradingview") {
        this.fibSettings.levels = [
          { ratio: 0.0, label: "0.0%", color: "#94a3b8", width: 1, style: 2, enabled: true },
          { ratio: 0.236, label: "23.6%", color: "#38bdf8", width: 1, style: 2, enabled: true },
          { ratio: 0.382, label: "38.2%", color: "#f59e0b", width: 1, style: 2, enabled: true },
          { ratio: 0.500, label: "50.0% (Eq)", color: "#ec4899", width: 1.5, style: 0, enabled: true },
          { ratio: 0.618, label: "61.8% (Golden)", color: "#10b981", width: 2, style: 0, enabled: true },
          { ratio: 0.786, label: "78.6%", color: "#a855f7", width: 1, style: 2, enabled: true },
          { ratio: 1.000, label: "100.0%", color: "#94a3b8", width: 1, style: 2, enabled: true },
          { ratio: 1.618, label: "161.8% (Ext)", color: "#06b6d4", width: 1.5, style: 2, enabled: true },
        ];
      } else if (presetName === "ict") {
        this.fibSettings.levels = [
          { ratio: 0.0, label: "0.0% (Low)", color: "#64748b", width: 1, style: 2, enabled: true },
          { ratio: 0.500, label: "50.0% (Equilibrium)", color: "#38bdf8", width: 1.5, style: 0, enabled: true },
          { ratio: 0.620, label: "62.0% (OTE Entry)", color: "#10b981", width: 2, style: 0, enabled: true },
          { ratio: 0.705, label: "70.5% (Sweet Spot)", color: "#f59e0b", width: 2, style: 0, enabled: true },
          { ratio: 0.790, label: "79.0% (Deep OTE)", color: "#ec4899", width: 2, style: 0, enabled: true },
          { ratio: 1.000, label: "100.0% (High)", color: "#64748b", width: 1, style: 2, enabled: true },
          { ratio: -0.27, label: "-27.0% (Target 1)", color: "#a855f7", width: 1.5, style: 2, enabled: true },
          { ratio: -0.62, label: "-62.0% (Target 2)", color: "#06b6d4", width: 1.5, style: 2, enabled: true },
        ];
      } else if (presetName === "neon") {
        this.fibSettings.levels = [
          { ratio: 0.0, label: "0.0%", color: "#38bdf8", width: 1, style: 0, enabled: true },
          { ratio: 0.236, label: "23.6%", color: "#22d3ee", width: 1, style: 2, enabled: true },
          { ratio: 0.382, label: "38.2%", color: "#facc15", width: 1, style: 2, enabled: true },
          { ratio: 0.500, label: "50.0%", color: "#f43f5e", width: 2, style: 0, enabled: true },
          { ratio: 0.618, label: "61.8%", color: "#4ade80", width: 2, style: 0, enabled: true },
          { ratio: 0.786, label: "78.6%", color: "#c084fc", width: 1, style: 2, enabled: true },
          { ratio: 1.000, label: "100.0%", color: "#38bdf8", width: 1, style: 0, enabled: true },
          { ratio: 1.618, label: "161.8%", color: "#e879f9", width: 2, style: 2, enabled: true },
        ];
      } else if (presetName === "monochrome") {
        this.fibSettings.levels = [
          { ratio: 0.0, label: "0.0%", color: "#94a3b8", width: 1, style: 0, enabled: true },
          { ratio: 0.236, label: "23.6%", color: "#64748b", width: 1, style: 2, enabled: true },
          { ratio: 0.382, label: "38.2%", color: "#94a3b8", width: 1, style: 2, enabled: true },
          { ratio: 0.500, label: "50.0%", color: "#e2e8f0", width: 2, style: 0, enabled: true },
          { ratio: 0.618, label: "61.8%", color: "#ffffff", width: 2, style: 0, enabled: true },
          { ratio: 0.786, label: "78.6%", color: "#94a3b8", width: 1, style: 2, enabled: true },
          { ratio: 1.000, label: "100.0%", color: "#94a3b8", width: 1, style: 0, enabled: true },
        ];
      }
      this.renderFibSettingsList();
    }

    handleChartClick(param) {
      if (!param || !param.point || !this.candleSeries) return;
      const clickedPrice = this.candleSeries.coordinateToPrice(param.point.y);
      if (clickedPrice == null || isNaN(clickedPrice) || clickedPrice <= 0) return;

      // 1. Fibonacci Drawing Mode (Click-Click fallback)
      if (this.fibMode && !this.isDraggingFib) {
        if (this.fibStep === 1) {
          this.fibAnchor1 = clickedPrice;
          this.fibStep = 2;
          this.dom.chartActionText.innerText = `📐 Fib Anchor 1 set at ₹${clickedPrice.toFixed(2)}. Move mouse or click Point 2...`;
          this.audio.playClick();
        } else if (this.fibStep === 2) {
          this.lastFibPoints = { p1: this.fibAnchor1, p2: clickedPrice };
          this.drawFibRetracement(this.fibAnchor1, clickedPrice);
          this.cancelChartAction();
          this.audio.playClick();
        }
        return;
      }

      // 2. Interactive Stop Loss Pick
      if (this.chartPickMode === "SL") {
        this.applyChartPickedSL(clickedPrice);
        return;
      }

      // 3. Interactive Target Pick
      if (this.chartPickMode === "TARGET") {
        this.applyChartPickedTarget(clickedPrice);
        return;
      }
    }

    startFibDrawing() {
      this.cancelChartAction();
      this.fibMode = true;
      this.fibStep = 1;
      this.fibAnchor1 = null;
      this.isDraggingFib = false;
      this.dom.btnDrawFib.classList.add("active");
      this.dom.chartActionText.innerText = "📐 Fibonacci: Drag across chart, or click 2 points to draw...";
      this.dom.chartActionBanner.classList.remove("hidden");
      this.audio.playClick();
    }

    autoSwingFib() {
      if (!this.session || !this.session.candles.length) return;
      const visible = this.session.candles.slice(0, this.currentBarIndex + 1);
      let minLow = Infinity;
      let maxHigh = -Infinity;
      visible.forEach(c => {
        if (c.low < minLow) minLow = c.low;
        if (c.high > maxHigh) maxHigh = c.high;
      });

      if (!isFinite(minLow) || !isFinite(maxHigh) || minLow === maxHigh) {
        minLow = this.session.candles[0].low;
        maxHigh = this.session.candles[0].high;
      }

      const dayOpen = visible[0].open;
      const curClose = visible[visible.length - 1].close;
      // In uptrend, anchor Low to High; in downtrend, anchor High to Low
      if (curClose >= dayOpen) {
        this.lastFibPoints = { p1: minLow, p2: maxHigh };
        this.drawFibRetracement(minLow, maxHigh);
      } else {
        this.lastFibPoints = { p1: maxHigh, p2: minLow };
        this.drawFibRetracement(maxHigh, minLow);
      }
      this.audio.playClick();
    }

    drawFibRetracement(p1, p2) {
      this.clearFib();
      this.lastFibPoints = { p1, p2 };
      this.lastDrawnFibP2 = p2;
      const diff = p2 - p1;

      const levels = (this.fibSettings && Array.isArray(this.fibSettings.levels))
        ? this.fibSettings.levels
        : this.getDefaultFibSettings().levels;
      const showPrices = this.fibSettings ? this.fibSettings.showPrices !== false : true;
      const showLabels = this.fibSettings ? this.fibSettings.showLabels !== false : true;

      levels.forEach(lvl => {
        if (lvl.enabled === false) return;
        const lvlPrice = p1 + diff * lvl.ratio;
        const titleParts = ["Fib"];
        if (showLabels && lvl.label) titleParts.push(lvl.label);
        if (showPrices) titleParts.push(`(₹${lvlPrice.toFixed(1)})`);

        const line = this.candleSeries.createPriceLine({
          price: lvlPrice,
          color: lvl.color || "#38bdf8",
          lineWidth: lvl.width || 1,
          lineStyle: (typeof lvl.style === "number") ? lvl.style : 2,
          axisLabelVisible: true,
          title: titleParts.join(" ")
        });
        this.fibLines.push(line);
      });
    }

    clearFib() {
      if (this.fibLines && this.candleSeries) {
        this.fibLines.forEach(l => {
          try { this.candleSeries.removePriceLine(l); } catch (e) {}
        });
      }
      this.fibLines = [];
    }

    startChartPick(type) {
      this.cancelChartAction();
      this.chartPickMode = type;
      if (type === "SL") {
        this.dom.btnChartPickSL.classList.add("active");
        this.dom.btnChartSLQuick.classList.add("active");
        this.dom.chartActionText.innerText = "🛑 Click anywhere on the chart canvas to set Stop Loss...";
      } else {
        this.dom.btnChartPickTarget.classList.add("active");
        this.dom.btnChartTargetQuick.classList.add("active");
        this.dom.chartActionText.innerText = "🎯 Click anywhere on the chart canvas to set Target...";
      }
      this.dom.chartActionBanner.classList.remove("hidden");
      this.audio.playClick();
    }

    cancelChartAction() {
      this.fibMode = false;
      this.fibStep = 0;
      this.fibAnchor1 = null;
      this.isDraggingFib = false;
      if (this.chart) {
        this.chart.applyOptions({
          handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: true }
        });
      }
      this.chartPickMode = null;
      this.dom.chartActionBanner.classList.add("hidden");
      this.dom.btnDrawFib.classList.remove("active");
      this.dom.btnChartPickSL.classList.remove("active");
      this.dom.btnChartPickTarget.classList.remove("active");
      this.dom.btnChartSLQuick.classList.remove("active");
      this.dom.btnChartTargetQuick.classList.remove("active");
    }

    applyChartPickedSL(clickedSpotPrice) {
      if (!this.session) return;

      if (this.instrumentType === "futures") {
        this.customSLPrice = Math.round(clickedSpotPrice * 100) / 100;
        this.dom.inputSLPrice.value = this.customSLPrice.toFixed(2);
        document.querySelectorAll(".preset-chip[data-sl]").forEach(b => b.classList.remove("active"));
        this.cancelChartAction();
        this.updateOrderSummary();
        this.audio.playClick();
        return;
      }

      const spot = this.session.candles[this.currentBarIndex].close;
      const T = OptionsEngine.calculateTimeToExpiry(this.currentBarIndex, this.session.total_bars, this.selectedExpiry);
      const iv = this.session.default_iv || 0.16;
      const opt = OptionsEngine.price(spot, this.selectedStrike || spot, T, 0.07, iv, this.selectedDirection);
      const delta = Math.max(0.15, Math.abs(opt.delta));

      // Calculate underlying spot distance
      let spotDistance = Math.abs(spot - clickedSpotPrice);
      if (spotDistance < 1) {
        spotDistance = Math.max(5, Math.round(spot * 0.005));
      }

      // Translate spot points to option points
      const optionPointsRisk = Math.max(0.5, Math.round(spotDistance * delta * 100) / 100);
      let optionSL = Math.max(0.05, Math.round((opt.price - optionPointsRisk) * 100) / 100);

      // Ensure SL is strictly below entry price
      if (optionSL >= opt.price) {
        optionSL = Math.max(0.05, Math.round(opt.price * 0.85 * 100) / 100);
      }

      this.customSLPrice = optionSL;
      this.dom.inputSLPrice.value = this.customSLPrice.toFixed(2);
      document.querySelectorAll(".preset-chip[data-sl]").forEach(b => b.classList.remove("active"));
      this.cancelChartAction();
      this.updateOrderSummary();
      this.audio.playClick();
    }

    applyChartPickedTarget(clickedSpotPrice) {
      if (!this.session) return;

      if (this.instrumentType === "futures") {
        this.customTargetPrice = Math.round(clickedSpotPrice * 100) / 100;
        this.dom.inputTargetPrice.value = this.customTargetPrice.toFixed(2);
        document.querySelectorAll(".preset-chip[data-target]").forEach(b => b.classList.remove("active"));
        this.cancelChartAction();
        this.updateOrderSummary();
        this.audio.playClick();
        return;
      }

      const spot = this.session.candles[this.currentBarIndex].close;
      const T = OptionsEngine.calculateTimeToExpiry(this.currentBarIndex, this.session.total_bars, this.selectedExpiry);
      const iv = this.session.default_iv || 0.16;
      const opt = OptionsEngine.price(spot, this.selectedStrike || spot, T, 0.07, iv, this.selectedDirection);
      const delta = Math.max(0.15, Math.abs(opt.delta));

      // Calculate underlying spot distance
      let spotDistance = Math.abs(clickedSpotPrice - spot);
      if (spotDistance < 1) {
        spotDistance = Math.max(10, Math.round(spot * 0.01));
      }

      // Translate spot points to option points
      const optionPointsGain = Math.max(0.5, Math.round(spotDistance * delta * 100) / 100);
      const optionTarget = Math.round((opt.price + optionPointsGain) * 100) / 100;

      this.customTargetPrice = Math.max(opt.price + 0.1, optionTarget);
      this.dom.inputTargetPrice.value = this.customTargetPrice.toFixed(2);
      document.querySelectorAll(".preset-chip[data-target]").forEach(b => b.classList.remove("active"));
      this.cancelChartAction();
      this.updateOrderSummary();
      this.audio.playClick();
    }

    evaluatePositionStep(candle) {
      if (!this.activePosition) return;

      const pos = this.activePosition;

      // FUTURES INTRA-BAR EVALUATION
      if (pos.instrumentType === "futures") {
        pos.currentPrice = candle.close;
        const isLong = pos.direction === "LONG";

        // 1. Check Target Hit
        if ((isLong && candle.high >= pos.targetPrice) || (!isLong && candle.low <= pos.targetPrice)) {
          this.closePosition(pos.targetPrice, "TARGET_HIT", candle);
          return;
        }

        // 2. Check Stop Loss Hit
        if ((isLong && candle.low <= pos.slPrice) || (!isLong && candle.high >= pos.slPrice)) {
          this.closePosition(pos.slPrice, "STOP_LOSS_HIT", candle);
          return;
        }

        // 3. EOD Auto Square-off at 15:25
        if (this.currentBarIndex >= this.session.total_bars - 1) {
          this.closePosition(candle.close, "EOD_SQUAREOFF", candle);
          return;
        }

        // Live MTM PnL
        pos.pnl = isLong
          ? Math.round((pos.currentPrice - pos.entryPrice) * pos.qty * 100) / 100
          : Math.round((pos.entryPrice - pos.currentPrice) * pos.qty * 100) / 100;
        pos.roiPct = pos.marginBlocked > 0
          ? Math.round((pos.pnl / pos.marginBlocked) * 1000) / 10
          : 0;

        this.renderActivePositionDeck();
        this.updateHUD();
        return;
      }

      // OPTIONS INTRA-BAR EVALUATION
      const iv = this.session.default_iv || 0.16;
      const T = OptionsEngine.calculateTimeToExpiry(this.currentBarIndex, this.session.total_bars, pos.expiry);

      // Intra-bar extremes
      const extremes = OptionsEngine.barExtremes(candle, pos.strike, T, 0.07, iv, pos.direction);
      pos.currentPrice = extremes.close;

      // 1. Check if Target reached during this candle
      if (extremes.high >= pos.targetPrice) {
        this.closePosition(pos.targetPrice, "TARGET_HIT", candle);
        return;
      }

      // 2. Check if Stop Loss breached during this candle
      if (extremes.low <= pos.slPrice) {
        this.closePosition(pos.slPrice, "STOP_LOSS_HIT", candle);
        return;
      }

      // 3. Check for EOD auto square-off at 15:25 (bar 74)
      if (this.currentBarIndex >= this.session.total_bars - 1) {
        this.closePosition(extremes.close, "EOD_SQUAREOFF", candle);
        return;
      }

      // Live MTM PnL
      pos.pnl = Math.round((pos.currentPrice - pos.entryPrice) * pos.qty * 100) / 100;
      pos.roiPct = Math.round(((pos.currentPrice - pos.entryPrice) / pos.entryPrice) * 1000) / 10;

      this.renderActivePositionDeck();
      this.updateHUD();
    }

    renderActivePositionDeck() {
      if (!this.activePosition) {
        this.dom.positionDeck.classList.add("hidden");
        this.dom.tradeChartOverlay.classList.add("hidden");
        return;
      }

      const pos = this.activePosition;
      const isFutures = pos.instrumentType === "futures";
      this.dom.positionDeck.classList.remove("hidden");
      this.dom.tradeChartOverlay.classList.remove("hidden");

      // Badge
      if (isFutures) {
        this.dom.posSymbolTag.innerText = `${pos.symbol} FUT [${pos.direction}]`;
        this.dom.posCapitalDeployed.innerText = `Margin: ₹${pos.marginBlocked.toLocaleString("en-IN")}`;
      } else {
        this.dom.posSymbolTag.innerText = `${pos.symbol} ${pos.strike} ${pos.direction} [${pos.expiry.toUpperCase()}]`;
        this.dom.posCapitalDeployed.innerText = `Capital: ₹${pos.totalCost.toLocaleString("en-IN")}`;
      }

      // Live PnL
      const sign = pos.pnl >= 0 ? "+" : "";
      this.dom.posLivePnl.innerText = `${sign}₹ ${pos.pnl.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
      this.dom.posLivePnl.className = `pnl-amount font-mono ${pos.pnl >= 0 ? "positive" : "negative"}`;

      this.dom.posLiveRoi.innerText = `${sign}${pos.roiPct.toFixed(1)}%`;
      this.dom.posLiveRoi.className = `roi-tag ${pos.pnl >= 0 ? "positive" : "negative"}`;

      // Progress Track between SL and Target
      this.dom.posSlVal.innerText = `SL: ₹${pos.slPrice.toFixed(2)}`;
      this.dom.posCurVal.innerText = `LTP: ₹${pos.currentPrice.toFixed(2)}`;
      this.dom.posTgVal.innerText = `Target: ₹${pos.targetPrice.toFixed(2)}`;

      const isShort = isFutures && pos.direction === "SHORT";
      let pct;
      if (isShort) {
        const totalRange = pos.slPrice - pos.targetPrice;
        pct = totalRange > 0 ? ((pos.slPrice - pos.currentPrice) / totalRange) * 100 : 50;
      } else {
        const totalRange = pos.targetPrice - pos.slPrice;
        pct = totalRange > 0 ? ((pos.currentPrice - pos.slPrice) / totalRange) * 100 : 50;
      }
      pct = Math.max(0, Math.min(100, pct));
      this.dom.meterMarker.style.left = `${pct}%`;

      // Chart Overlay pill
      const overlayBadge = document.getElementById("overlay-strike-badge");
      if (overlayBadge) {
        overlayBadge.innerText = isFutures ? `${pos.symbol} FUT ${pos.direction}` : `${pos.strike} ${pos.direction}`;
      }
      document.getElementById("overlay-qty").innerText = `${pos.qty} Qty`;
      document.getElementById("overlay-entry").innerText = `Entry: ₹${pos.entryPrice.toFixed(2)}`;
      document.getElementById("overlay-cur").innerText = `LTP: ₹${pos.currentPrice.toFixed(2)}`;
      document.getElementById("overlay-pnl").innerText = `${sign}₹${pos.pnl} (${sign}${pos.roiPct}%)`;
      document.getElementById("overlay-pnl").className = `overlay-pnl font-mono ${pos.pnl >= 0 ? "positive" : "negative"}`;
    }

    closePosition(exitPrice, reason, candle) {
      if (!this.activePosition) return;

      const pos = this.activePosition;
      const isFutures = pos.instrumentType === "futures";
      const actualExit = Math.max(0.05, Math.round(exitPrice * 100) / 100);

      let finalPnl;
      let finalRoi;
      let returnedFunds;

      if (isFutures) {
        const isLong = pos.direction === "LONG";
        finalPnl = isLong
          ? Math.round((actualExit - pos.entryPrice) * pos.qty * 100) / 100
          : Math.round((pos.entryPrice - actualExit) * pos.qty * 100) / 100;
        finalRoi = pos.marginBlocked > 0
          ? Math.round((finalPnl / pos.marginBlocked) * 1000) / 10
          : 0;
        returnedFunds = Math.round((pos.marginBlocked + finalPnl) * 100) / 100;
      } else {
        finalPnl = Math.round((actualExit - pos.entryPrice) * pos.qty * 100) / 100;
        finalRoi = Math.round(((actualExit - pos.entryPrice) / pos.entryPrice) * 1000) / 10;
        returnedFunds = Math.round(actualExit * pos.qty * 100) / 100;
      }

      // Update balances
      this.currentCapital = Math.round((this.currentCapital + returnedFunds) * 100) / 100;
      this.dayPnL = Math.round((this.dayPnL + finalPnl) * 100) / 100;
      this.totalTrades++;
      if (finalPnl > 0) this.wins++; else this.losses++;

      // Award XP
      const xpGain = finalPnl > 0 ? Math.max(50, Math.round(finalPnl / 100)) : 10;
      this.xp += xpGain;

      // Sound Effect
      if (reason === "TARGET_HIT") {
        this.audio.playTargetWin();
      } else if (reason === "STOP_LOSS_HIT") {
        this.audio.playStopLossHit();
      } else {
        this.audio.playClick();
      }

      // Add Exit Marker on Chart
      const exitTime = candle ? candle.time : this.session.candles[this.currentBarIndex].time;
      this.chartMarkers.push({
        time: exitTime,
        position: finalPnl >= 0 ? "aboveBar" : "belowBar",
        color: finalPnl >= 0 ? "#10b981" : "#f43f5e",
        shape: "circle",
        text: `${reason === "TARGET_HIT" ? "🎯 TARGET" : (reason === "STOP_LOSS_HIT" ? "🛑 SL" : "🚪 EXIT")} @ ₹${actualExit.toFixed(1)} (${finalPnl >= 0 ? "+" : ""}₹${finalPnl})`,
      });
      this.candleSeries.setMarkers(this.chartMarkers);

      // Record in journal
      const tradeRecord = {
        id: pos.id,
        time: `${pos.entryTime} → ${candle ? (candle.time_str || "15:30") : "Exit"}`,
        symbol: isFutures ? `${pos.symbol} FUT` : `${pos.symbol} ${pos.strike}`,
        type: isFutures ? (pos.direction === "LONG" ? "FUT_LONG" : "FUT_SHORT") : pos.direction,
        qty: pos.qty,
        buyPrice: isFutures ? (pos.direction === "LONG" ? pos.entryPrice : actualExit) : pos.entryPrice,
        sellPrice: isFutures ? (pos.direction === "LONG" ? actualExit : pos.entryPrice) : actualExit,
        reason: reason,
        pnl: finalPnl,
        roi: finalRoi
      };
      this.tradeJournal.unshift(tradeRecord);
      this.renderJournal();

      // Clear
      this.activePosition = null;
      this.clearPriceLines();
      this.dom.positionDeck.classList.add("hidden");
      this.dom.tradeChartOverlay.classList.add("hidden");

      // Save & Update HUD
      this.updateHUD();
      this.saveState();
      this.syncTradeToBackend(tradeRecord, pos);
    }

    async syncTradeToBackend(trade, pos) {
      try {
        await fetch("/api/game/trade", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            trade_id: trade.id,
            symbol: pos.symbol,
            instrument_type: pos.instrumentType || "options",
            strike: pos.strike || 0,
            option_type: pos.direction,
            expiry_type: pos.expiry || "monthly",
            lot_size: pos.lotSize,
            lots: pos.lots,
            quantity: pos.qty,
            entry_bar: pos.entryBar,
            exit_bar: this.currentBarIndex,
            entry_time: pos.entryTime,
            exit_time: trade.time.split("→")[1].trim(),
            entry_price: pos.entryPrice,
            exit_price: trade.sellPrice,
            target_price: pos.targetPrice,
            stop_loss_price: pos.slPrice,
            pnl: trade.pnl,
            pnl_pct: trade.roi,
            exit_reason: trade.reason
          })
        });
      } catch (e) {
        console.warn("Backend trade sync:", e);
      }
    }

    moveSLToCost() {
      if (!this.activePosition) return;
      this.activePosition.slPrice = this.activePosition.entryPrice;
      this.audio.playClick();
      this.drawPositionChartLines();
      this.renderActivePositionDeck();
    }

    trailSL() {
      if (!this.activePosition) return;
      const pos = this.activePosition;
      if (pos.instrumentType === "futures") {
        const step = Math.max(1, Math.round(pos.entryPrice * 0.002)); // ~0.2%
        if (pos.direction === "LONG") {
          pos.slPrice = Math.min(pos.currentPrice - 2, pos.slPrice + step);
        } else {
          pos.slPrice = Math.max(pos.currentPrice + 2, pos.slPrice - step);
        }
      } else {
        const step = (pos.entryPrice * 0.1);
        pos.slPrice = Math.round((pos.slPrice + step) * 100) / 100;
      }
      this.audio.playClick();
      this.drawPositionChartLines();
      this.renderActivePositionDeck();
    }

    // ========================================================================
    // JOURNAL & HUD
    // ========================================================================
    renderJournal() {
      this.dom.journalTradeCount.innerText = `${this.tradeJournal.length} Trades`;
      const winCount = this.tradeJournal.filter(t => t.pnl > 0).length;
      const winRate = this.tradeJournal.length > 0 ? ((winCount / this.tradeJournal.length) * 100).toFixed(1) : 0;
      this.dom.journalWinrate.innerText = `${winRate}%`;

      const sign = this.dayPnL >= 0 ? "+" : "";
      this.dom.journalTotalPnl.innerText = `${sign}₹ ${this.dayPnL.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
      this.dom.journalTotalPnl.className = this.dayPnL >= 0 ? "positive" : "negative";

      if (!this.tradeJournal.length) {
        this.dom.journalTbody.innerHTML = `
          <tr class="empty-row"><td colspan="10">No closed trades yet in this session. Take an option bet above to start journaling!</td></tr>
        `;
        return;
      }

      const rows = this.tradeJournal.map((t, i) => {
        const pnlClass = t.pnl >= 0 ? "positive" : "negative";
        const reasonBadge = t.reason === "TARGET_HIT" ? "🎯 Target Hit" :
          (t.reason === "STOP_LOSS_HIT" ? "🛑 Stop Loss Hit" : (t.reason === "EOD_SQUAREOFF" ? "⏰ 15:30 EOD" : "🚪 Market Exit"));

        return `
          <tr>
            <td>#${this.tradeJournal.length - i}</td>
            <td>${t.time}</td>
            <td><b>${t.symbol}</b></td>
            <td><span class="moneyness-tag ${t.type === "CE" ? "ITM" : "OTM"}">${t.type}</span></td>
            <td>${t.qty}</td>
            <td>₹${t.buyPrice.toFixed(2)}</td>
            <td>₹${t.sellPrice.toFixed(2)}</td>
            <td>${reasonBadge}</td>
            <td class="${pnlClass}"><b>${t.pnl >= 0 ? "+" : ""}₹${t.pnl.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</b></td>
            <td class="${pnlClass}">${t.roi >= 0 ? "+" : ""}${t.roi.toFixed(1)}%</td>
          </tr>
        `;
      });

      this.dom.journalTbody.innerHTML = rows.join("");
    }

    updateHUD() {
      // Calculate live total equity & live day PnL (realized + unrealized MTM)
      const unrealizedPnL = this.activePosition ? (this.activePosition.pnl || 0) : 0;
      const liveDayPnL = Math.round((this.dayPnL + unrealizedPnL) * 100) / 100;
      const activePositionValue = this.activePosition ? (this.activePosition.currentPrice * this.activePosition.qty) : 0;
      const totalEquity = Math.round((this.currentCapital + activePositionValue) * 100) / 100;

      this.dom.hudCapital.innerText = `₹ ${Math.round(totalEquity).toLocaleString("en-IN")}`;

      const sign = liveDayPnL >= 0 ? "+" : "";
      const pnlPct = this.startingCapital > 0 ? ((liveDayPnL / this.startingCapital) * 100).toFixed(2) : "0.00";
      this.dom.hudPnl.innerHTML = `${sign}₹ ${liveDayPnL.toLocaleString("en-IN", { minimumFractionDigits: 2 })} <span class="stat-pct">(${sign}${pnlPct}%)</span>`;
      this.dom.hudPnl.className = `stat-value font-mono ${liveDayPnL >= 0 ? "positive" : "negative"}`;

      // Rank & XP
      if (this.xp < 500) this.rank = "Floor Trader";
      else if (this.xp < 1500) this.rank = "Prop Trader";
      else if (this.xp < 3500) this.rank = "Senior Scalper";
      else if (this.xp < 7500) this.rank = "Hedge Fund PM";
      else this.rank = "Market Maker Titan";

      this.dom.hudRankBadge.innerText = this.rank;
      const xpProgress = Math.min(100, Math.round((this.xp % 1000) / 10));
      this.dom.hudXpBar.style.width = `${xpProgress}%`;
    }

    updateAudioButtonState() {
      if (this.audio.enabled) {
        this.dom.btnAudioToggle.classList.add("active");
        this.dom.audioIcon.innerText = "🔊";
      } else {
        this.dom.btnAudioToggle.classList.remove("active");
        this.dom.audioIcon.innerText = "🔇";
      }
    }

    // ========================================================================
    // END OF DAY (EOD) PERFORMANCE REPORT MODAL
    // ========================================================================
    onEndOfDayReached() {
      // Auto square off any open position
      if (this.activePosition) {
        const lastCandle = this.session.candles[this.session.total_bars - 1];
        this.closePosition(this.activePosition.currentPrice, "EOD_SQUAREOFF", lastCandle);
      }

      const winCount = this.tradeJournal.filter(t => t.pnl > 0).length;
      const winRate = this.tradeJournal.length > 0 ? ((winCount / this.tradeJournal.length) * 100).toFixed(1) : "0.0";
      const grossProfit = this.tradeJournal.filter(t => t.pnl > 0).reduce((acc, t) => acc + t.pnl, 0);
      const grossLoss = Math.abs(this.tradeJournal.filter(t => t.pnl < 0).reduce((acc, t) => acc + t.pnl, 0));
      const pf = grossLoss > 0 ? (grossProfit / grossLoss).toFixed(2) : (grossProfit > 0 ? "∞" : "0.0");
      const baseCap = (typeof this.dayStartCapital === "number" && this.dayStartCapital > 0) ? this.dayStartCapital : (this.startingCapital || 1000000);
      const roi = baseCap > 0 ? ((this.dayPnL / baseCap) * 100).toFixed(2) : "0.0";

      const sign = this.dayPnL >= 0 ? "+" : "";
      document.getElementById("eod-pnl-hero").innerText = `${sign}₹ ${this.dayPnL.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
      document.getElementById("eod-pnl-hero").className = `eod-pnl-val font-mono ${this.dayPnL >= 0 ? "positive" : "negative"}`;
      document.getElementById("eod-roi-hero").innerText = `${sign}${roi}% Day ROI`;

      document.getElementById("eod-trades").innerText = this.tradeJournal.length;
      document.getElementById("eod-winrate").innerText = `${winRate}%`;
      document.getElementById("eod-pf").innerText = pf;
      document.getElementById("eod-xp").innerText = `+${Math.max(50, Math.round(grossProfit / 100))} XP`;

      // Tier Name
      let tier = "Disciplined Scalper ⭐⭐";
      if (parseFloat(winRate) >= 70 && this.dayPnL > 0) tier = "S-Tier Dalal Street Sniper ⭐⭐⭐";
      else if (this.dayPnL > 0) tier = "Profitable Prop Trader ⭐⭐";
      else tier = "Risk Management Apprentice ⭐";
      document.getElementById("eod-tier-name").innerText = tier;

      this.saveState();
      this.dom.modalEod.classList.remove("hidden");
    }

    // ========================================================================
    // EVENT BINDINGS
    // ========================================================================
    bindEvents() {
      // Mode Selector
      this.dom.btnModeIndex.addEventListener("click", () => {
        this.dom.btnModeIndex.classList.add("active");
        this.dom.btnModeStock.classList.remove("active");
        this.dom.indexPills.classList.remove("hidden");
        this.dom.stockSelectWrapper.classList.add("hidden");
        this.currentMode = "index";
        this.currentSymbol = "NIFTY";
        this.startNewSession("NIFTY");
      });

      this.dom.btnModeStock.addEventListener("click", () => {
        this.dom.btnModeStock.classList.add("active");
        this.dom.btnModeIndex.classList.remove("active");
        this.dom.indexPills.classList.add("hidden");
        this.dom.stockSelectWrapper.classList.remove("hidden");
        this.currentMode = "stock";
        this.currentSymbol = this.dom.stockSelect.value;
        this.startNewSession(this.currentSymbol);
      });

      // Index Pills
      this.dom.indexPills.querySelectorAll(".pill-btn").forEach(btn => {
        btn.addEventListener("click", () => {
          this.dom.indexPills.querySelectorAll(".pill-btn").forEach(b => b.classList.remove("active"));
          btn.classList.add("active");
          const sym = btn.getAttribute("data-symbol");
          this.currentSymbol = sym;
          this.startNewSession(sym);
        });
      });

      // Stock Dropdown & Random Stock
      this.dom.stockSelect.addEventListener("change", (e) => {
        this.currentSymbol = e.target.value;
        this.startNewSession(this.currentSymbol);
      });

      this.dom.btnRandomStock.addEventListener("click", () => {
        const opts = Array.from(this.dom.stockSelect.options);
        const randomOpt = opts[Math.floor(Math.random() * opts.length)].value;
        this.dom.stockSelect.value = randomOpt;
        this.currentSymbol = randomOpt;
        this.startNewSession(randomOpt);
      });

      // New Mystery Day
      this.dom.btnNewDay.addEventListener("click", () => {
        this.startNewSession();
      });

      // Blind Mode Toggle
      this.dom.btnToggleBlind.addEventListener("click", () => {
        this.blindMode = !this.blindMode;
        if (this.blindMode) {
          this.dom.btnToggleBlind.classList.add("active");
          this.dom.blindLabel.innerText = "Blind ON";
        } else {
          this.dom.btnToggleBlind.classList.remove("active");
          this.dom.blindLabel.innerText = "Blind OFF";
        }
        this.updateHeaderAndInfo();
        this.audio.playClick();
      });

      // Replay Deck
      this.dom.btnReplayPlay.addEventListener("click", () => this.togglePlay());
      this.dom.btnReplayStep.addEventListener("click", () => this.stepNextBar());
      this.dom.btnReplayRestart.addEventListener("click", () => this.restartDay());
      this.dom.timelineSlider.addEventListener("input", (e) => this.jumpToBar(e.target.value));

      document.querySelectorAll(".speed-selector .segment-btn").forEach(btn => {
        btn.addEventListener("click", () => {
          document.querySelectorAll(".speed-selector .segment-btn").forEach(b => b.classList.remove("active"));
          btn.classList.add("active");
          this.setSpeed(btn.getAttribute("data-speed"));
          this.audio.playClick();
        });
      });

      // Technical Overlays
      [
        this.dom.toggleEma9,
        this.dom.toggleEma21,
        this.dom.toggleEma50,
        this.dom.toggleMa200,
        this.dom.toggleVwap,
        this.dom.toggleSupertrend
      ].filter(Boolean).forEach(btn => {
        btn.addEventListener("click", () => {
          btn.classList.toggle("active");
          this.renderCurrentChartState();
          this.audio.playClick();
        });
      });

      // Instrument Type Switcher (Options vs Futures)
      if (this.dom.btnInstOptions) {
        this.dom.btnInstOptions.addEventListener("click", () => this.switchInstrumentType("options"));
      }
      if (this.dom.btnInstFutures) {
        this.dom.btnInstFutures.addEventListener("click", () => this.switchInstrumentType("futures"));
      }

      // Futures Direction Bias (Long vs Short)
      if (this.dom.btnFutLong) {
        this.dom.btnFutLong.addEventListener("click", () => this.setFuturesDirection("LONG"));
      }
      if (this.dom.btnFutShort) {
        this.dom.btnFutShort.addEventListener("click", () => this.setFuturesDirection("SHORT"));
      }

      // Expiry selector
      document.querySelectorAll(".expiry-selector .segment-btn").forEach(btn => {
        btn.addEventListener("click", () => {
          document.querySelectorAll(".expiry-selector .segment-btn").forEach(b => b.classList.remove("active"));
          btn.classList.add("active");
          this.selectedExpiry = btn.getAttribute("data-expiry");
          this.audio.playClick();
          if (this.session) this.renderStrikeMatrix(this.session.candles[this.currentBarIndex].close);
        });
      });

      // Direction Call / Put
      this.dom.btnOptCall.addEventListener("click", () => {
        this.dom.btnOptCall.classList.add("active");
        this.dom.btnOptPut.classList.remove("active");
        this.selectedDirection = "CE";
        this.audio.playClick();
        if (this.session) this.renderStrikeMatrix(this.session.candles[this.currentBarIndex].close);
      });

      this.dom.btnOptPut.addEventListener("click", () => {
        this.dom.btnOptPut.classList.add("active");
        this.dom.btnOptCall.classList.remove("active");
        this.selectedDirection = "PE";
        this.audio.playClick();
        if (this.session) this.renderStrikeMatrix(this.session.candles[this.currentBarIndex].close);
      });

      // Chart Drawing & Interactive Placing Tools
      if (this.dom.btnFitChart) {
        this.dom.btnFitChart.addEventListener("click", () => {
          this.resetChartViewport(false);
          this.audio.playClick();
        });
      }
      this.dom.btnDrawFib.addEventListener("click", () => this.startFibDrawing());
      if (this.dom.btnFibSettings) {
        this.dom.btnFibSettings.addEventListener("click", () => this.openFibSettingsModal());
      }
      if (this.dom.btnCloseFibSettings) {
        this.dom.btnCloseFibSettings.addEventListener("click", () => this.dom.modalFibSettings.classList.add("hidden"));
      }
      if (this.dom.btnCancelFibSettings) {
        this.dom.btnCancelFibSettings.addEventListener("click", () => this.dom.modalFibSettings.classList.add("hidden"));
      }
      if (this.dom.btnSaveFibSettings) {
        this.dom.btnSaveFibSettings.addEventListener("click", () => {
          if (this.dom.fibOptPrices) this.fibSettings.showPrices = this.dom.fibOptPrices.checked;
          if (this.dom.fibOptLabels) this.fibSettings.showLabels = this.dom.fibOptLabels.checked;
          this.saveFibSettings();
          this.dom.modalFibSettings.classList.add("hidden");
          this.audio.playClick();
          if (this.lastFibPoints) {
            this.drawFibRetracement(this.lastFibPoints.p1, this.lastFibPoints.p2);
          }
        });
      }
      if (this.dom.btnResetFibDefaults) {
        this.dom.btnResetFibDefaults.addEventListener("click", () => {
          this.fibSettings = this.getDefaultFibSettings();
          this.renderFibSettingsList();
          if (this.dom.fibOptPrices) this.dom.fibOptPrices.checked = true;
          if (this.dom.fibOptLabels) this.dom.fibOptLabels.checked = true;
          this.saveFibSettings();
          this.audio.playClick();
          if (this.lastFibPoints) {
            this.drawFibRetracement(this.lastFibPoints.p1, this.lastFibPoints.p2);
          }
        });
      }
      if (this.dom.btnFibAddLevel) {
        this.dom.btnFibAddLevel.addEventListener("click", () => {
          this.fibSettings.levels.push({
            ratio: 0.5,
            label: "Custom",
            color: "#38bdf8",
            width: 1,
            style: 2,
            enabled: true
          });
          this.renderFibSettingsList();
        });
      }
      document.querySelectorAll("[data-fib-preset]").forEach(btn => {
        btn.addEventListener("click", () => {
          document.querySelectorAll("[data-fib-preset]").forEach(b => b.classList.remove("active"));
          btn.classList.add("active");
          this.applyFibPreset(btn.getAttribute("data-fib-preset"));
        });
      });
      this.dom.btnAutoFib.addEventListener("click", () => this.autoSwingFib());
      this.dom.btnClearFib.addEventListener("click", () => {
        this.clearFib();
        this.audio.playClick();
      });
      this.dom.btnChartPickTarget.addEventListener("click", () => this.startChartPick("TARGET"));
      this.dom.btnChartPickSL.addEventListener("click", () => this.startChartPick("SL"));
      this.dom.btnChartSLQuick.addEventListener("click", () => this.startChartPick("SL"));
      this.dom.btnChartTargetQuick.addEventListener("click", () => this.startChartPick("TARGET"));
      this.dom.btnCancelChartAction.addEventListener("click", () => this.cancelChartAction());

      // Position Sizing: Risk % vs Fixed Lots Mode
      this.dom.btnSizingRisk.addEventListener("click", () => {
        this.sizingMode = "risk";
        this.dom.btnSizingRisk.classList.add("active");
        this.dom.btnSizingLots.classList.remove("active");
        this.dom.boxRiskSizing.classList.remove("hidden");
        this.dom.boxManualLots.classList.add("hidden");
        this.audio.playClick();
        this.updateOrderSummary();
      });

      this.dom.btnSizingLots.addEventListener("click", () => {
        this.sizingMode = "lots";
        this.dom.btnSizingLots.classList.add("active");
        this.dom.btnSizingRisk.classList.remove("active");
        this.dom.boxManualLots.classList.remove("hidden");
        this.dom.boxRiskSizing.classList.add("hidden");
        this.audio.playClick();
        this.updateOrderSummary();
      });

      // Risk % Chips
      document.querySelectorAll(".risk-chip").forEach(btn => {
        btn.addEventListener("click", () => {
          document.querySelectorAll(".risk-chip").forEach(b => b.classList.remove("active"));
          btn.classList.add("active");
          this.selectedRiskPct = parseFloat(btn.getAttribute("data-risk"));
          this.dom.inputCustomRisk.value = this.selectedRiskPct;
          this.audio.playClick();
          this.updateOrderSummary();
        });
      });

      this.dom.inputCustomRisk.addEventListener("input", (e) => {
        const val = parseFloat(e.target.value);
        if (!isNaN(val) && val > 0) {
          this.selectedRiskPct = val;
          document.querySelectorAll(".risk-chip").forEach(b => b.classList.remove("active"));
          this.updateOrderSummary();
        }
      });

      // Lots Pills & Input
      document.querySelectorAll(".lot-quick-pills .lot-pill:not(.max)").forEach(btn => {
        btn.addEventListener("click", () => {
          this.sizingMode = "lots";
          this.dom.btnSizingLots.classList.add("active");
          this.dom.btnSizingRisk.classList.remove("active");
          this.dom.boxManualLots.classList.remove("hidden");
          this.dom.boxRiskSizing.classList.add("hidden");
          document.querySelectorAll(".lot-quick-pills .lot-pill").forEach(b => b.classList.remove("active"));
          btn.classList.add("active");
          this.selectedLots = parseInt(btn.getAttribute("data-lots"));
          this.dom.inputLots.value = this.selectedLots;
          this.audio.playClick();
          this.updateOrderSummary();
        });
      });

      this.dom.btnLotMax.addEventListener("click", () => {
        if (!this.session) return;
        this.sizingMode = "lots";
        this.dom.btnSizingLots.classList.add("active");
        this.dom.btnSizingRisk.classList.remove("active");
        this.dom.boxManualLots.classList.remove("hidden");
        this.dom.boxRiskSizing.classList.add("hidden");

        if (this.instrumentType === "futures") {
          const candle = this.session.candles[this.currentBarIndex];
          const spot = candle.close;
          const lot = this.session.lot_size;
          const marginRate = (this.session.instrument_type === "stock" || this.currentMode === "stock") ? 0.15 : 0.125;
          const marginPerLot = Math.round(spot * lot * marginRate);
          const maxLots = marginPerLot > 0 ? Math.max(1, Math.floor(this.currentCapital / marginPerLot)) : 10;
          this.selectedLots = Math.min(100, maxLots);
          this.dom.inputLots.value = this.selectedLots;
          this.dom.btnLotMax.classList.add("active");
          this.audio.playClick();
          this.updateOrderSummary();
          return;
        }

        const candle = this.session.candles[this.currentBarIndex];
        const opt = OptionsEngine.price(candle.close, this.selectedStrike, 0.01, 0.07, 0.16, this.selectedDirection);
        const costPerLot = opt.price * this.session.lot_size;
        const maxLots = costPerLot > 0 ? Math.max(1, Math.floor(this.currentCapital / costPerLot)) : 10;
        this.selectedLots = Math.min(100, maxLots);
        this.dom.inputLots.value = this.selectedLots;
        this.dom.btnLotMax.classList.add("active");
        this.audio.playClick();
        this.updateOrderSummary();
      });

      this.dom.inputLots.addEventListener("input", (e) => {
        this.sizingMode = "lots";
        this.dom.btnSizingLots.classList.add("active");
        this.dom.btnSizingRisk.classList.remove("active");
        this.dom.boxManualLots.classList.remove("hidden");
        this.dom.boxRiskSizing.classList.add("hidden");
        this.selectedLots = Math.max(1, parseInt(e.target.value) || 1);
        this.updateOrderSummary();
      });

      // Stop Loss Presets & Manual Input
      document.querySelectorAll(".preset-chip[data-sl]").forEach(btn => {
        btn.addEventListener("click", () => {
          document.querySelectorAll(".preset-chip[data-sl]").forEach(b => b.classList.remove("active"));
          btn.classList.add("active");
          this.customSLPrice = null;
          if (this.instrumentType === "futures") {
            this.selectedFutSLPct = parseFloat(btn.getAttribute("data-sl"));
          } else {
            this.selectedSLPct = parseFloat(btn.getAttribute("data-sl"));
          }
          this.audio.playClick();
          this.updateOrderSummary();
        });
      });

      this.dom.inputSLPrice.addEventListener("input", (e) => {
        const val = parseFloat(e.target.value);
        if (!isNaN(val) && val > 0) {
          if (!this.session) return;
          if (this.instrumentType === "futures") {
            this.customSLPrice = val;
            document.querySelectorAll(".preset-chip[data-sl]").forEach(b => b.classList.remove("active"));
            this.updateOrderSummary();
            return;
          }

          const spot = this.session.candles[this.currentBarIndex].close;
          const T = OptionsEngine.calculateTimeToExpiry(this.currentBarIndex, this.session.total_bars, this.selectedExpiry);
          const iv = this.session.default_iv || 0.16;
          const opt = OptionsEngine.price(spot, this.selectedStrike || spot, T, 0.07, iv, this.selectedDirection);
          const delta = Math.max(0.15, Math.abs(opt.delta));

          // If typed price is like the underlying spot level (e.g. 23950 on Nifty or 2900 on Reliance):
          if (val > (opt.price * 2.5) && val > 300) {
            const spotDist = Math.abs(spot - val);
            const optLoss = Math.max(0.5, spotDist * delta);
            this.customSLPrice = Math.max(0.05, Math.round((opt.price - optLoss) * 100) / 100);
          } else {
            // Direct Option Premium SL
            this.customSLPrice = Math.max(0.05, Math.min(opt.price - 0.5, val));
          }
          document.querySelectorAll(".preset-chip[data-sl]").forEach(b => b.classList.remove("active"));
          this.updateOrderSummary();
        } else {
          this.customSLPrice = null;
          this.updateOrderSummary();
        }
      });

      // Target Presets & Manual Input
      document.querySelectorAll(".preset-chip[data-target]").forEach(btn => {
        btn.addEventListener("click", () => {
          document.querySelectorAll(".preset-chip[data-target]").forEach(b => b.classList.remove("active"));
          btn.classList.add("active");
          this.customTargetPrice = null;
          if (this.instrumentType === "futures") {
            this.selectedFutTargetPct = parseFloat(btn.getAttribute("data-target"));
          } else {
            this.selectedTargetPct = parseFloat(btn.getAttribute("data-target"));
          }
          this.audio.playClick();
          this.updateOrderSummary();
        });
      });

      this.dom.inputTargetPrice.addEventListener("input", (e) => {
        const val = parseFloat(e.target.value);
        if (!isNaN(val) && val > 0) {
          if (!this.session) return;
          if (this.instrumentType === "futures") {
            this.customTargetPrice = val;
            document.querySelectorAll(".preset-chip[data-target]").forEach(b => b.classList.remove("active"));
            this.updateOrderSummary();
            return;
          }

          const spot = this.session.candles[this.currentBarIndex].close;
          const T = OptionsEngine.calculateTimeToExpiry(this.currentBarIndex, this.session.total_bars, this.selectedExpiry);
          const iv = this.session.default_iv || 0.16;
          const opt = OptionsEngine.price(spot, this.selectedStrike || spot, T, 0.07, iv, this.selectedDirection);
          const delta = Math.max(0.15, Math.abs(opt.delta));

          // If typed price is like the underlying spot level (e.g. 24150 on Nifty):
          if (val > (opt.price * 2.5) && val > 300) {
            const spotDist = Math.abs(val - spot);
            const optGain = Math.max(0.5, spotDist * delta);
            this.customTargetPrice = Math.max(opt.price + 0.1, Math.round((opt.price + optGain) * 100) / 100);
          } else {
            // Direct Option Premium Target
            this.customTargetPrice = Math.max(opt.price + 0.1, val);
          }
          document.querySelectorAll(".preset-chip[data-target]").forEach(b => b.classList.remove("active"));
          this.updateOrderSummary();
        } else {
          this.customTargetPrice = null;
          this.updateOrderSummary();
        }
      });

      // Execute Order
      this.dom.btnExecuteOrder.addEventListener("click", () => this.executeOrder());

      // Active Position Actions
      this.dom.btnExitPosition.addEventListener("click", () => {
        if (this.activePosition) {
          this.closePosition(this.activePosition.currentPrice, "MANUAL_EXIT", this.session.candles[this.currentBarIndex]);
        }
      });
      this.dom.btnSlBreakeven.addEventListener("click", () => this.moveSLToCost());
      this.dom.btnTrailSl.addEventListener("click", () => this.trailSL());

      // Drawer Collapse / Expand
      this.dom.drawerToggleBtn.addEventListener("click", () => {
        this.dom.appFooterDrawer.classList.toggle("expanded");
      });

      // Audio Toggle
      this.dom.btnAudioToggle.addEventListener("click", () => {
        this.audio.enabled = !this.audio.enabled;
        this.updateAudioButtonState();
        this.saveState();
      });

      // Starting Capital & Reset Modal
      this.dom.hudBalanceBtn.addEventListener("click", () => {
        this.dom.modalSettings.classList.remove("hidden");
      });
      this.dom.btnCloseSettings.addEventListener("click", () => {
        this.dom.modalSettings.classList.add("hidden");
      });
      this.dom.btnCancelSettings.addEventListener("click", () => {
        this.dom.modalSettings.classList.add("hidden");
      });

      document.querySelectorAll(".capital-card").forEach(card => {
        card.addEventListener("click", () => {
          document.querySelectorAll(".capital-card").forEach(c => c.classList.remove("active"));
          card.classList.add("active");
          this.dom.inputCustomCapital.value = card.getAttribute("data-cap");
        });
      });

      this.dom.btnSaveCapital.addEventListener("click", async () => {
        const val = parseFloat(this.dom.inputCustomCapital.value) || 1000000;
        this.startingCapital = val;
        this.currentCapital = val;
        this.dayStartCapital = val;
        this.dayPnL = 0;
        this.totalTrades = 0;
        this.wins = 0;
        this.losses = 0;
        this.tradeJournal = [];
        this.renderJournal();
        this.updateHUD();
        this.saveState();
        this.dom.modalSettings.classList.add("hidden");
        this.audio.playClick();

        try {
          await fetch("/api/game/reset-account", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ starting_balance: val })
          });
        } catch (e) {}
      });

      // Help Modal
      this.dom.btnHelpModal.addEventListener("click", () => {
        this.dom.modalHelp.classList.remove("hidden");
      });
      this.dom.btnCloseHelp.addEventListener("click", () => {
        this.dom.modalHelp.classList.add("hidden");
      });
      if (this.dom.btnGotIt) {
        this.dom.btnGotIt.addEventListener("click", () => {
          this.dom.modalHelp.classList.add("hidden");
        });
      }

      // EOD Modal Actions
      this.dom.btnEodNextDay.addEventListener("click", () => {
        this.dom.modalEod.classList.add("hidden");
        this.startNewSession();
      });
      this.dom.btnEodReplayDay.addEventListener("click", () => {
        this.dom.modalEod.classList.add("hidden");
        this.restartDay();
      });
      this.dom.btnEodClose.addEventListener("click", () => {
        this.dom.modalEod.classList.add("hidden");
        this.dom.appFooterDrawer.classList.add("expanded");
      });

      // Keyboard Shortcuts
      window.addEventListener("keydown", (e) => {
        // Ignore if user typing in input
        if (["INPUT", "SELECT", "TEXTAREA"].includes(e.target.tagName)) return;

        if (e.code === "Space") {
          e.preventDefault();
          this.togglePlay();
        } else if (e.code === "ArrowRight") {
          e.preventDefault();
          this.stepNextBar();
        } else if (e.key === "r" || e.key === "R") {
          e.preventDefault();
          this.restartDay();
        } else if (e.key === "b" || e.key === "B") {
          e.preventDefault();
          this.dom.btnOptCall.click();
        } else if (e.key === "p" || e.key === "P") {
          e.preventDefault();
          this.dom.btnOptPut.click();
        } else if (e.key === "x" || e.key === "X") {
          e.preventDefault();
          if (this.activePosition) {
            this.closePosition(this.activePosition.currentPrice, "MANUAL_EXIT", this.session.candles[this.currentBarIndex]);
          }
        } else if (e.key === "Escape") {
          this.cancelChartAction();
        }
      });
    }
  }

  // Launch when DOM is ready
  window.addEventListener("DOMContentLoaded", () => {
    window.gameApp = new GameApp();
  });
})();
