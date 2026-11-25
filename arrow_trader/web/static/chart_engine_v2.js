/**
 * ARROW TRADE PRO 2.0 // TradingView-Style Chart Engine (KLineChart v9)
 * Features:
 *  - High-DPI TradingView-grade candlesticks, crosshair, OHLCV tooltip, & volume pane
 *  - Multi-Timeframe Aggregation (5m, 15m, 30m, 1H, 4H)
 *  - Synchronized Right-Side Higher Timeframe (HTF) Split Chart
 *  - Key Session Liquidity Levels: PDH, PDL, Asia H/L, London H/L, NY H/L
 *  - Custom Indicators: EMA 9, EMA 21, EMA 50, MA 200, VWAP, Supertrend
 *  - Interactive Drawing Tools: Fibonacci Retracement, Trendline, Horizontal Line, Zone Box
 */
(function (window) {
  "use strict";

  const TF_MINUTES = {
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1H": 60,
    "4H": 240,
  };

  let indicatorsRegistered = false;

  function registerCustomKLineComponents() {
    if (indicatorsRegistered || !window.klinecharts) return;
    indicatorsRegistered = true;

    const kc = window.klinecharts;

    // Helper for EMA calculation
    function registerEma(name, shortName, period, color, lineWidth = 1.5) {
      kc.registerIndicator({
        name,
        shortName,
        series: "price",
        calcParams: [period],
        precision: 2,
        styles: {
          lines: [{ color, size: lineWidth, style: "solid", smooth: false, dashedValue: [2, 2] }],
        },
        figures: [{ key: "ema", title: `${shortName}: `, type: "line" }],
        calc: (dataList, indicator) => {
          if (!dataList || !dataList.length) return [];
          const p = indicator.calcParams[0] || period;
          const k = 2 / (p + 1);
          let emaVal = null;
          return dataList.map((d) => {
            if (emaVal === null) {
              emaVal = d.close;
            } else {
              emaVal = d.close * k + emaVal * (1 - k);
            }
            return { ema: emaVal };
          });
        },
      });
    }

    registerEma("ARROW_EMA9", "EMA9", 9, "#38bdf8", 1.5);
    registerEma("ARROW_EMA21", "EMA21", 21, "#f59e0b", 1.5);
    registerEma("ARROW_EMA50", "EMA50", 50, "#a855f7", 1.7);

    // 200 SMA
    kc.registerIndicator({
      name: "ARROW_MA200",
      shortName: "MA200",
      series: "price",
      calcParams: [200],
      precision: 2,
      styles: {
        lines: [{ color: "#f97316", size: 2.0, style: "solid", smooth: false, dashedValue: [2, 2] }],
      },
      figures: [{ key: "ma", title: "MA200: ", type: "line" }],
      calc: (dataList, indicator) => {
        if (!dataList || !dataList.length) return [];
        const p = indicator.calcParams[0] || 200;
        let sum = 0;
        return dataList.map((d, i) => {
          sum += d.close;
          if (i >= p) sum -= dataList[i - p].close;
          const count = Math.min(i + 1, p);
          return i >= Math.min(20, p - 1) ? { ma: sum / count } : {};
        });
      },
    });

    // Intraday VWAP (resets on date change)
    kc.registerIndicator({
      name: "ARROW_VWAP",
      shortName: "VWAP",
      series: "price",
      calcParams: [],
      precision: 2,
      styles: {
        lines: [{ color: "#8b5cf6", size: 1.6, style: "solid", smooth: false, dashedValue: [2, 2] }],
      },
      figures: [{ key: "vwap", title: "VWAP: ", type: "line" }],
      calc: (dataList) => {
        if (!dataList || !dataList.length) return [];
        let cumPV = 0;
        let cumVol = 0;
        let lastDay = null;
        return dataList.map((d) => {
          const dayKey = new Date(d.timestamp).toISOString().slice(0, 10);
          if (dayKey !== lastDay) {
            cumPV = 0;
            cumVol = 0;
            lastDay = dayKey;
          }
          const tp = (d.high + d.low + d.close) / 3;
          const vol = d.volume || 1;
          cumPV += tp * vol;
          cumVol += vol;
          return { vwap: cumVol > 0 ? cumPV / cumVol : tp };
        });
      },
    });

    // Supertrend (10, 3)
    kc.registerIndicator({
      name: "ARROW_SUPERTREND",
      shortName: "ST(10,3)",
      series: "price",
      calcParams: [10, 3.0],
      precision: 2,
      styles: {
        lines: [
          { color: "#10b981", size: 2.0, style: "solid", smooth: false, dashedValue: [2, 2] },
          { color: "#f43f5e", size: 2.0, style: "solid", smooth: false, dashedValue: [2, 2] },
        ],
      },
      figures: [
        { key: "up", title: "ST+: ", type: "line" },
        { key: "down", title: "ST-: ", type: "line" },
      ],
      calc: (dataList, indicator) => {
        const period = indicator.calcParams[0] || 10;
        const mult = indicator.calcParams[1] || 3.0;
        if (!dataList.length) return [];

        const trArr = [];
        for (let i = 0; i < dataList.length; i++) {
          const c = dataList[i];
          if (i === 0) {
            trArr.push(c.high - c.low);
          } else {
            const pc = dataList[i - 1].close;
            trArr.push(Math.max(c.high - c.low, Math.abs(c.high - pc), Math.abs(c.low - pc)));
          }
        }

        const atrArr = [];
        let atr = 0;
        for (let i = 0; i < trArr.length; i++) {
          if (i < period) {
            atr += trArr[i] / Math.max(1, Math.min(period, i + 1));
            if (i === period - 1) {
              atr = trArr.slice(0, period).reduce((a, b) => a + b, 0) / period;
            }
          } else {
            atr = (atr * (period - 1) + trArr[i]) / period;
          }
          atrArr.push(atr);
        }

        const out = [];
        let finalUpper = 0;
        let finalLower = 0;
        let dir = 1;

        for (let i = 0; i < dataList.length; i++) {
          const c = dataList[i];
          const hl2 = (c.high + c.low) / 2;
          const basicUpper = hl2 + mult * atrArr[i];
          const basicLower = hl2 - mult * atrArr[i];

          if (i === 0) {
            finalUpper = basicUpper;
            finalLower = basicLower;
            out.push({});
            continue;
          }

          const prevClose = dataList[i - 1].close;
          finalUpper = basicUpper < finalUpper || prevClose > finalUpper ? basicUpper : finalUpper;
          finalLower = basicLower > finalLower || prevClose < finalLower ? basicLower : finalLower;

          if (dir === 1 && c.close < finalLower) {
            dir = -1;
          } else if (dir === -1 && c.close > finalUpper) {
            dir = 1;
          }

          if (i < period) {
            out.push({});
          } else if (dir === 1) {
            out.push({ up: finalLower });
          } else {
            out.push({ down: finalUpper });
          }
        }
        return out;
      },
    });

    // Custom TradingView-style horizontal level overlay with crisp pill badge
    kc.registerOverlay({
      name: "arrowLevelLine",
      totalStep: 2,
      needDefaultPointFigure: false,
      needDefaultXAxisFigure: false,
      needDefaultYAxisFigure: false,
      createPointFigures: ({ coordinates, bounding, overlay }) => {
        if (!coordinates || !coordinates.length || !coordinates[0]) return [];
        const y = coordinates[0].y;
        const ext = overlay.extendData || {};
        const color = ext.color || "#f59e0b";
        const label = ext.label || "";
        const priceStr = ext.priceText || "";
        const dashed = ext.dashed !== false;

        const figures = [
          {
            type: "line",
            attrs: {
              coordinates: [
                { x: 0, y },
                { x: bounding.width, y },
              ],
            },
            styles: {
              style: dashed ? "dashed" : "solid",
              color,
              size: ext.lineWidth || 1.4,
              dashedValue: ext.dashedValue || [5, 4],
            },
          },
        ];

        if (label) {
          const textContent = priceStr ? `${label}  ${priceStr}` : label;
          figures.push({
            type: "text",
            attrs: {
              x: ext.align === "right" ? bounding.width - 12 : 12,
              y: y - 4,
              text: textContent,
              align: ext.align === "right" ? "right" : "left",
              baseline: "bottom",
            },
            styles: {
              color: "#ffffff",
              size: 10,
              family: "'JetBrains Mono', monospace",
              weight: "600",
              backgroundColor: color,
              borderRadius: 4,
              paddingLeft: 6,
              paddingRight: 6,
              paddingTop: 2,
              paddingBottom: 2,
            },
          });
        }

        return figures;
      },
    });
  }

  function getChartThemeStyles() {
    return {
      grid: {
        show: true,
        horizontal: {
          show: true,
          size: 1,
          color: "rgba(255, 255, 255, 0.04)",
          style: "solid",
        },
        vertical: {
          show: true,
          size: 1,
          color: "rgba(255, 255, 255, 0.04)",
          style: "solid",
        },
      },
      candle: {
        type: "candle_solid",
        bar: {
          upColor: "#10b981",
          downColor: "#f43f5e",
          noChangeColor: "#94a3b8",
          upBorderColor: "#10b981",
          downBorderColor: "#f43f5e",
          noChangeBorderColor: "#94a3b8",
          upWickColor: "#10b981",
          downWickColor: "#f43f5e",
          noChangeWickColor: "#94a3b8",
        },
        priceMark: {
          show: true,
          high: { show: true, color: "#94a3b8", textSize: 10 },
          low: { show: true, color: "#94a3b8", textSize: 10 },
          last: {
            show: true,
            upColor: "#10b981",
            downColor: "#f43f5e",
            noChangeColor: "#94a3b8",
            line: { show: true, style: "dashed", dashedValue: [4, 4], size: 1 },
            text: { show: true, size: 11, color: "#ffffff", borderRadius: 4 },
          },
        },
        tooltip: {
          showRule: "always",
          showType: "standard",
          custom: [
            { title: "O: ", value: "{open}" },
            { title: "H: ", value: "{high}" },
            { title: "L: ", value: "{low}" },
            { title: "C: ", value: "{close}" },
            { title: "V: ", value: "{volume}" },
          ],
          text: {
            size: 11,
            family: "'JetBrains Mono', monospace",
            color: "#cbd5e1",
          },
        },
      },
      indicator: {
        tooltip: {
          showRule: "always",
          showType: "standard",
          text: {
            size: 10,
            family: "'JetBrains Mono', monospace",
          },
        },
      },
      xAxis: {
        show: true,
        axisLine: { show: true, color: "rgba(255, 255, 255, 0.08)" },
        tickLine: { show: true, color: "rgba(255, 255, 255, 0.12)" },
        tickText: { color: "#64748b", size: 10, family: "'JetBrains Mono', monospace" },
      },
      yAxis: {
        show: true,
        axisLine: { show: true, color: "rgba(255, 255, 255, 0.08)" },
        tickLine: { show: true, color: "rgba(255, 255, 255, 0.12)" },
        tickText: { color: "#94a3b8", size: 10, family: "'JetBrains Mono', monospace" },
      },
      crosshair: {
        show: true,
        horizontal: {
          show: true,
          line: { show: true, style: "dashed", dashedValue: [4, 2], size: 1, color: "#38bdf8" },
          text: { show: true, backgroundColor: "#0284c7", color: "#ffffff", size: 11, family: "'JetBrains Mono', monospace" },
        },
        vertical: {
          show: true,
          line: { show: true, style: "dashed", dashedValue: [4, 2], size: 1, color: "#38bdf8" },
          text: { show: true, backgroundColor: "#0284c7", color: "#ffffff", size: 11, family: "'JetBrains Mono', monospace" },
        },
      },
      separator: {
        size: 1,
        color: "rgba(255, 255, 255, 0.07)",
      },
    };
  }

  class ArrowChartEngineV2 {
    constructor() {
      this.mainChart = null;
      this.htfChart = null;
      this.mainEl = null;
      this.htfEl = null;

      this.mainTf = "5m";
      this.htfTf = "15m";
      this.htfVisible = true;

      this.activeIndicators = {
        ema9: true,
        ema21: true,
        ema50: true,
        ma200: true,
        vwap: true,
        supertrend: true,
      };

      this.levelOverlayIds = { main: [], htf: [] };
      this.tradeOverlayIds = { main: [], htf: [] };
      this.previewOverlayIds = [];
      this.fibOverlayIds = [];
      this.userOverlayIds = [];

      this._onPricePickCallback = null;
      this._onCrosshairBarCallback = null;
      this._latestBars = [];
      this._lastPrecision = 2;
    }

    init(mainEl, htfEl, callbacks = {}) {
      if (!window.klinecharts) {
        console.error("KLineChart library not loaded!");
        return false;
      }

      registerCustomKLineComponents();

      this.mainEl = mainEl;
      this.htfEl = htfEl;
      this._onPricePickCallback = callbacks.onPricePick || null;
      this._onCrosshairBarCallback = callbacks.onCrosshairBar || null;

      // Initialize Main Chart
      this.mainChart = window.klinecharts.init(mainEl, {
        styles: getChartThemeStyles(),
      });
      this.mainChart.setOffsetRightDistance(60);
      this.mainChart.createIndicator("VOL", false, { height: 68 });
      this.syncIndicators(this.activeIndicators);

      // Initialize Right-Side HTF Chart
      if (htfEl) {
        this.htfChart = window.klinecharts.init(htfEl, {
          styles: getChartThemeStyles(),
        });
        this.htfChart.setOffsetRightDistance(45);
        this.htfChart.createIndicator("VOL", false, { height: 50 });
        this.htfChart.createIndicator("ARROW_EMA9", true, { id: "candle_pane" });
        this.htfChart.createIndicator("ARROW_EMA21", true, { id: "candle_pane" });
        this.htfChart.createIndicator("ARROW_EMA50", true, { id: "candle_pane" });
        this.htfChart.createIndicator("ARROW_VWAP", true, { id: "candle_pane" });
      }

      // Click listener for Place Target / Place SL
      mainEl.addEventListener("click", (ev) => {
        if (!this._onPricePickCallback || !this.mainChart) return;
        const rect = mainEl.getBoundingClientRect();
        const x = ev.clientX - rect.left;
        const y = ev.clientY - rect.top;
        try {
          const pts = this.mainChart.convertFromPixel([{ x, y }], { paneId: "candle_pane" });
          if (pts && pts[0] && typeof pts[0].value === "number" && !isNaN(pts[0].value)) {
            this._onPricePickCallback(pts[0].value, pts[0].timestamp);
          }
        } catch (err) {
          console.warn("Chart coordinate pick warning:", err);
        }
      });

      // Crosshair hover callback
      this.mainChart.subscribeAction("onCrosshairChange", (data) => {
        if (this._onCrosshairBarCallback && data && data.kLineData) {
          this._onCrosshairBarCallback(data.kLineData);
        }
      });

      // Auto-resize observer
      if (typeof ResizeObserver !== "undefined") {
        const ro = new ResizeObserver(() => this.resize());
        if (mainEl.parentElement) ro.observe(mainEl.parentElement);
        if (htfEl && htfEl.parentElement) ro.observe(htfEl.parentElement);
      } else {
        window.addEventListener("resize", () => this.resize());
      }

      return true;
    }

    aggregateCandles(bars5m, tf) {
      if (!bars5m || !bars5m.length) return [];
      const mins = TF_MINUTES[tf] || 5;
      const bucketMs = mins * 60 * 1000;

      if (mins === 5) {
        return bars5m.map((b) => ({
          timestamp: (b.time > 1e12 ? b.time : b.time * 1000),
          open: Number(b.open),
          high: Number(b.high),
          low: Number(b.low),
          close: Number(b.close),
          volume: Number(b.volume || 0),
        }));
      }

      const map = new Map();
      for (const b of bars5m) {
        const tsMs = b.time > 1e12 ? b.time : b.time * 1000;
        const bucket = Math.floor(tsMs / bucketMs) * bucketMs;
        if (!map.has(bucket)) {
          map.set(bucket, {
            timestamp: bucket,
            open: Number(b.open),
            high: Number(b.high),
            low: Number(b.low),
            close: Number(b.close),
            volume: Number(b.volume || 0),
          });
        } else {
          const agg = map.get(bucket);
          agg.high = Math.max(agg.high, Number(b.high));
          agg.low = Math.min(agg.low, Number(b.low));
          agg.close = Number(b.close);
          agg.volume += Number(b.volume || 0);
        }
      }
      return Array.from(map.values()).sort((a, b) => a.timestamp - b.timestamp);
    }

    updateData(priorCandles, visibleTodayCandles, precision = 2) {
      const combined = [...(priorCandles || []), ...(visibleTodayCandles || [])];
      this._latestBars = combined;
      this._lastPrecision = precision;

      if (!combined.length) {
        if (this.mainChart && this.mainChart.clearData) this.mainChart.clearData();
        if (this.htfChart && this.htfChart.clearData) this.htfChart.clearData();
        return;
      }

      if (this.mainChart) {
        this.mainChart.setPriceVolumePrecision(precision, 0);
        const mainBars = this.aggregateCandles(combined, this.mainTf);
        this.mainChart.applyNewData(mainBars);
      }

      if (this.htfChart && this.htfVisible) {
        this.htfChart.setPriceVolumePrecision(precision, 0);
        const htfBars = this.aggregateCandles(combined, this.htfTf);
        this.htfChart.applyNewData(htfBars);
      }
    }

    setMainTimeframe(tf) {
      if (!TF_MINUTES[tf]) return;
      this.mainTf = tf;
      if (this.mainChart && this._latestBars.length) {
        const mainBars = this.aggregateCandles(this._latestBars, this.mainTf);
        this.mainChart.applyNewData(mainBars);
        this.mainChart.scrollToRealTime();
      }
    }

    setHtfTimeframe(tf) {
      if (!TF_MINUTES[tf]) return;
      this.htfTf = tf;
      if (this.htfChart && this._latestBars.length) {
        const htfBars = this.aggregateCandles(this._latestBars, this.htfTf);
        this.htfChart.applyNewData(htfBars);
        this.htfChart.scrollToRealTime();
      }
    }

    setHtfVisible(visible) {
      this.htfVisible = !!visible;
      if (this.htfVisible && this.htfChart && this._latestBars.length) {
        setTimeout(() => {
          this.resize();
          const htfBars = this.aggregateCandles(this._latestBars, this.htfTf);
          this.htfChart.applyNewData(htfBars);
          this.htfChart.scrollToRealTime();
        }, 30);
      } else {
        setTimeout(() => this.resize(), 30);
      }
    }

    setChartStyle(type) {
      if (this.mainChart) {
        this.mainChart.setStyles({ candle: { type } });
      }
      if (this.htfChart) {
        this.htfChart.setStyles({ candle: { type } });
      }
    }

    syncIndicators(activeMap) {
      this.activeIndicators = Object.assign({}, this.activeIndicators, activeMap);
      if (!this.mainChart) return;

      const mapping = {
        ema9: "ARROW_EMA9",
        ema21: "ARROW_EMA21",
        ema50: "ARROW_EMA50",
        ma200: "ARROW_MA200",
        vwap: "ARROW_VWAP",
        supertrend: "ARROW_SUPERTREND",
      };

      for (const [key, indName] of Object.entries(mapping)) {
        try {
          this.mainChart.removeIndicator("candle_pane", indName);
        } catch (e) {}
        if (this.activeIndicators[key]) {
          this.mainChart.createIndicator(indName, true, { id: "candle_pane" });
        }
      }
    }

    syncSessionLevels(levels, enabledMap) {
      // Clear existing level overlays from both charts
      if (this.mainChart) {
        this.levelOverlayIds.main.forEach((id) => {
          try { this.mainChart.removeOverlay(id); } catch (e) {}
        });
      }
      if (this.htfChart) {
        this.levelOverlayIds.htf.forEach((id) => {
          try { this.htfChart.removeOverlay(id); } catch (e) {}
        });
      }
      this.levelOverlayIds = { main: [], htf: [] };

      if (!levels || !this._latestBars.length) return;

      const specs = [];
      if (enabledMap.pdh && typeof levels.pdh === "number") {
        specs.push({ price: levels.pdh, label: "PDH", color: "#f59e0b", dashedValue: [6, 3] });
      }
      if (enabledMap.pdl && typeof levels.pdl === "number") {
        specs.push({ price: levels.pdl, label: "PDL", color: "#f59e0b", dashedValue: [6, 3] });
      }
      if (enabledMap.asia) {
        if (typeof levels.asia_high === "number") specs.push({ price: levels.asia_high, label: "ASIA H", color: "#06b6d4", dashedValue: [3, 3] });
        if (typeof levels.asia_low === "number") specs.push({ price: levels.asia_low, label: "ASIA L", color: "#06b6d4", dashedValue: [3, 3] });
      }
      if (enabledMap.london) {
        if (typeof levels.london_high === "number") specs.push({ price: levels.london_high, label: "LDN H", color: "#a855f7", dashedValue: [4, 3] });
        if (typeof levels.london_low === "number") specs.push({ price: levels.london_low, label: "LDN L", color: "#a855f7", dashedValue: [4, 3] });
      }
      if (enabledMap.ny) {
        if (typeof levels.ny_high === "number") specs.push({ price: levels.ny_high, label: "NY H", color: "#10b981", dashedValue: [2, 3] });
        if (typeof levels.ny_low === "number") specs.push({ price: levels.ny_low, label: "NY L", color: "#f43f5e", dashedValue: [2, 3] });
      }

      const lastTs = this._latestBars.length
        ? (this._latestBars[this._latestBars.length - 1].time > 1e12
            ? this._latestBars[this._latestBars.length - 1].time
            : this._latestBars[this._latestBars.length - 1].time * 1000)
        : Date.now();

      for (const s of specs) {
        const overlayCfg = {
          name: "arrowLevelLine",
          lock: true,
          points: [{ timestamp: lastTs, value: s.price }],
          extendData: {
            label: s.label,
            priceText: s.price.toFixed(2),
            color: s.color,
            dashed: true,
            dashedValue: s.dashedValue,
            lineWidth: 1.3,
            align: "left",
          },
        };
        if (this.mainChart) {
          const id = this.mainChart.createOverlay(overlayCfg);
          if (id) this.levelOverlayIds.main.push(id);
        }
        if (this.htfChart) {
          const hId = this.htfChart.createOverlay(overlayCfg);
          if (hId) this.levelOverlayIds.htf.push(hId);
        }
      }
    }

    setTradeLines(entryPrice, targetPrice, slPrice, sideLabel = "ENTRY") {
      this.clearTradeLines();
      const lastTs = this._latestBars.length
        ? (this._latestBars[this._latestBars.length - 1].time > 1e12
            ? this._latestBars[this._latestBars.length - 1].time
            : this._latestBars[this._latestBars.length - 1].time * 1000)
        : Date.now();

      const addLine = (price, label, color) => {
        if (!price || isNaN(price)) return;
        const cfg = {
          name: "arrowLevelLine",
          lock: true,
          points: [{ timestamp: lastTs, value: Number(price) }],
          extendData: {
            label,
            priceText: Number(price).toFixed(2),
            color,
            dashed: label !== sideLabel,
            lineWidth: 1.8,
            align: "right",
          },
        };
        if (this.mainChart) {
          const id = this.mainChart.createOverlay(cfg);
          if (id) this.tradeOverlayIds.main.push(id);
        }
        if (this.htfChart) {
          const hId = this.htfChart.createOverlay(cfg);
          if (hId) this.tradeOverlayIds.htf.push(hId);
        }
      };

      addLine(entryPrice, sideLabel, "#38bdf8");
      if (targetPrice) addLine(targetPrice, "TARGET", "#10b981");
      if (slPrice) addLine(slPrice, "STOP LOSS", "#f43f5e");
    }

    clearTradeLines() {
      if (this.mainChart) {
        this.tradeOverlayIds.main.forEach((id) => {
          try { this.mainChart.removeOverlay(id); } catch (e) {}
        });
      }
      if (this.htfChart) {
        this.tradeOverlayIds.htf.forEach((id) => {
          try { this.htfChart.removeOverlay(id); } catch (e) {}
        });
      }
      this.tradeOverlayIds = { main: [], htf: [] };
    }

    setPreviewLines(targetPrice, slPrice) {
      this.clearPreviewLines();
      if (!this.mainChart) return;
      const lastTs = this._latestBars.length
        ? (this._latestBars[this._latestBars.length - 1].time > 1e12
            ? this._latestBars[this._latestBars.length - 1].time
            : this._latestBars[this._latestBars.length - 1].time * 1000)
        : Date.now();

      if (targetPrice) {
        const id = this.mainChart.createOverlay({
          name: "arrowLevelLine",
          lock: true,
          points: [{ timestamp: lastTs, value: Number(targetPrice) }],
          extendData: {
            label: "PREVIEW TP",
            priceText: Number(targetPrice).toFixed(2),
            color: "#10b981",
            dashed: true,
            align: "right",
          },
        });
        if (id) this.previewOverlayIds.push(id);
      }
      if (slPrice) {
        const id = this.mainChart.createOverlay({
          name: "arrowLevelLine",
          lock: true,
          points: [{ timestamp: lastTs, value: Number(slPrice) }],
          extendData: {
            label: "PREVIEW SL",
            priceText: Number(slPrice).toFixed(2),
            color: "#f43f5e",
            dashed: true,
            align: "right",
          },
        });
        if (id) this.previewOverlayIds.push(id);
      }
    }

    clearPreviewLines() {
      if (!this.mainChart) return;
      this.previewOverlayIds.forEach((id) => {
        try { this.mainChart.removeOverlay(id); } catch (e) {}
      });
      this.previewOverlayIds = [];
    }

    startDrawingTool(toolName) {
      if (!this.mainChart) return;
      const id = this.mainChart.createOverlay({ name: toolName });
      if (id) {
        if (toolName === "fibonacciLine") {
          this.fibOverlayIds.push(id);
        } else {
          this.userOverlayIds.push(id);
        }
      }
      return id;
    }

    drawAutoFib(lowPrice, highPrice, startTsSec, endTsSec) {
      this.clearFibs();
      if (!this.mainChart) return;
      const t1 = startTsSec > 1e12 ? startTsSec : startTsSec * 1000;
      const t2 = endTsSec > 1e12 ? endTsSec : endTsSec * 1000;
      const id = this.mainChart.createOverlay({
        name: "fibonacciLine",
        points: [
          { timestamp: t1, value: highPrice },
          { timestamp: t2, value: lowPrice },
        ],
      });
      if (id) this.fibOverlayIds.push(id);
    }

    clearFibs() {
      if (!this.mainChart) return;
      this.fibOverlayIds.forEach((id) => {
        try { this.mainChart.removeOverlay(id); } catch (e) {}
      });
      this.fibOverlayIds = [];
    }

    clearUserDrawings() {
      this.clearFibs();
      if (!this.mainChart) return;
      this.userOverlayIds.forEach((id) => {
        try { this.mainChart.removeOverlay(id); } catch (e) {}
      });
      this.userOverlayIds = [];
    }

    fitContent() {
      if (this.mainChart) this.mainChart.scrollToRealTime();
      if (this.htfChart) this.htfChart.scrollToRealTime();
    }

    resize() {
      if (this.mainChart) this.mainChart.resize();
      if (this.htfChart && this.htfVisible) this.htfChart.resize();
    }
  }

  window.ArrowChartEngineV2 = ArrowChartEngineV2;
})(window);
