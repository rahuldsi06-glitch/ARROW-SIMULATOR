#!/usr/bin/env python3
"""
Generates a standalone, beautiful HTML dashboard with interactive Equity Curve,
drawdown chart, monthly performance, strategy rulebook, and full trade log.
"""

import json

with open("/Users/rahul/Documents/Arrow_Algo_trader/backtest_data.json") as f:
    data = json.load(f)

json_payload = json.dumps(data)

html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>NIFTY 50 • ORB Strategy Backtest & Equity Curve Dashboard</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    body {{
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }}
    .mono {{
      font-family: 'JetBrains Mono', monospace;
    }}
    .glass {{
      background: rgba(17, 24, 39, 0.7);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
    }}
    .custom-scrollbar::-webkit-scrollbar {{
      width: 6px;
      height: 6px;
    }}
    .custom-scrollbar::-webkit-scrollbar-track {{
      background: rgba(31, 41, 55, 0.5);
    }}
    .custom-scrollbar::-webkit-scrollbar-thumb {{
      background: rgba(75, 85, 99, 0.8);
      border-radius: 9999px;
    }}
  </style>
</head>
<body class="bg-[#0b0f17] text-slate-100 min-h-screen antialiased selection:bg-emerald-500 selection:text-white pb-16">

  <!-- Top Navigation Header -->
  <header class="border-b border-slate-800/80 sticky top-0 z-50 glass bg-[#0b0f17]/80">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center font-bold text-slate-950 shadow-lg shadow-emerald-500/20 text-lg">
          📈
        </div>
        <div>
          <div class="flex items-center gap-2">
            <h1 class="font-bold text-base sm:text-lg text-white tracking-tight">NIFTY 50 • ORB Strategy Dashboard</h1>
            <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Live Backtest
            </span>
          </div>
          <p class="text-xs text-slate-400">Arrow Trade Broker Historical API (15-min candles • Jun–Oct 2026)</p>
        </div>
      </div>
      <div class="flex items-center gap-3 text-xs">
        <span class="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60 text-slate-300">
          <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          Token: 26000 (NIFTY)
        </span>
        <button onclick="window.print()" class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition flex items-center gap-1 font-medium">
          🖨️ Export / Print
        </button>
      </div>
    </div>
  </header>

  <!-- Main Container -->
  <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 space-y-8">

    <!-- Hero / Headline KPI Cards -->
    <section class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3.5">
      <!-- Card 1: Ending Capital -->
      <div class="bg-gradient-to-br from-slate-900 to-slate-900/60 border border-slate-800 p-4 rounded-2xl shadow-sm hover:border-slate-700 transition">
        <span class="text-xs font-medium text-slate-400">Ending Capital</span>
        <div class="mt-1 flex items-baseline gap-1.5">
          <span class="text-xl sm:text-2xl font-extrabold text-white mono">₹11.57L</span>
        </div>
        <div class="mt-1 flex items-center text-xs text-emerald-400 font-semibold gap-1">
          <span>+15.74% Net Return</span>
        </div>
      </div>

      <!-- Card 2: Net Profit -->
      <div class="bg-gradient-to-br from-slate-900 to-slate-900/60 border border-slate-800 p-4 rounded-2xl shadow-sm hover:border-slate-700 transition">
        <span class="text-xs font-medium text-slate-400">Net Profit</span>
        <div class="mt-1 flex items-baseline gap-1.5">
          <span class="text-xl sm:text-2xl font-extrabold text-emerald-400 mono">+₹1.57L</span>
        </div>
        <div class="mt-1 text-xs text-slate-400">
          From ₹10,00,000 base
        </div>
      </div>

      <!-- Card 3: Win Rate -->
      <div class="bg-gradient-to-br from-slate-900 to-slate-900/60 border border-slate-800 p-4 rounded-2xl shadow-sm hover:border-slate-700 transition">
        <span class="text-xs font-medium text-slate-400">Win Rate</span>
        <div class="mt-1 flex items-baseline gap-1.5">
          <span class="text-xl sm:text-2xl font-extrabold text-white mono">40.0%</span>
        </div>
        <div class="mt-1 text-xs text-slate-400">
          14 Wins / 21 Losses
        </div>
      </div>

      <!-- Card 4: Profit Factor -->
      <div class="bg-gradient-to-br from-slate-900 to-slate-900/60 border border-slate-800 p-4 rounded-2xl shadow-sm hover:border-slate-700 transition">
        <span class="text-xs font-medium text-slate-400">Profit Factor</span>
        <div class="mt-1 flex items-baseline gap-1.5">
          <span class="text-xl sm:text-2xl font-extrabold text-cyan-400 mono">1.74</span>
        </div>
        <div class="mt-1 text-xs text-slate-400">
          Gross: ₹3.69L / ₹2.11L
        </div>
      </div>

      <!-- Card 5: Sharpe Ratio -->
      <div class="bg-gradient-to-br from-slate-900 to-slate-900/60 border border-slate-800 p-4 rounded-2xl shadow-sm hover:border-slate-700 transition">
        <span class="text-xs font-medium text-slate-400">Sharpe Ratio</span>
        <div class="mt-1 flex items-baseline gap-1.5">
          <span class="text-xl sm:text-2xl font-extrabold text-indigo-400 mono">3.24</span>
        </div>
        <div class="mt-1 text-xs text-slate-400">
          Annualized risk-adjusted
        </div>
      </div>

      <!-- Card 6: Max Drawdown -->
      <div class="bg-gradient-to-br from-slate-900 to-slate-900/60 border border-slate-800 p-4 rounded-2xl shadow-sm hover:border-slate-700 transition">
        <span class="text-xs font-medium text-slate-400">Max Drawdown</span>
        <div class="mt-1 flex items-baseline gap-1.5">
          <span class="text-xl sm:text-2xl font-extrabold text-rose-400 mono">9.06%</span>
        </div>
        <div class="mt-1 text-xs text-slate-400">
          Peak-to-trough (Jun–Jul)
        </div>
      </div>
    </section>

    <!-- Interactive Equity Curve Chart Card -->
    <section class="bg-slate-900/90 border border-slate-800 rounded-3xl p-5 sm:p-7 shadow-xl">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <div class="flex items-center gap-2">
            <h2 class="text-lg font-bold text-white tracking-tight">Portfolio Equity Curve</h2>
            <span class="text-xs px-2 py-0.5 rounded-full bg-slate-800 border border-slate-700 text-slate-300">1 Trade/Day Max</span>
          </div>
          <p class="text-xs sm:text-sm text-slate-400 mt-0.5">Interactive capital trajectory across 35 executed trades with High-Water Mark and Drawdown overlay.</p>
        </div>
        
        <!-- Chart Controls -->
        <div class="flex items-center gap-2 self-start sm:self-auto">
          <button id="viewAllBtn" onclick="renderChart('ALL')" class="px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-500 text-slate-950 transition">All 4 Months</button>
          <button id="viewQ3Btn" onclick="renderChart('JUL_AUG')" class="px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition">Jul–Aug</button>
          <button id="viewQ4Btn" onclick="renderChart('SEP_OCT')" class="px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition">Sep–Oct</button>
        </div>
      </div>

      <!-- Canvas Chart Container -->
      <div class="relative mt-6 w-full" style="height: 380px;">
        <canvas id="equityChartCanvas" class="w-full h-full cursor-crosshair"></canvas>
        <div id="chartTooltip" class="absolute pointer-events-none hidden bg-slate-950/95 border border-slate-700 rounded-xl p-3 shadow-2xl text-xs z-20 backdrop-blur min-w-[200px]">
          <!-- dynamic tooltip content -->
        </div>
      </div>

      <!-- Chart Legend & Footer -->
      <div class="mt-4 pt-4 border-t border-slate-800/80 flex flex-wrap items-center justify-between text-xs text-slate-400 gap-3">
        <div class="flex items-center gap-5">
          <div class="flex items-center gap-2">
            <span class="w-3 h-3 rounded-full bg-emerald-400 inline-block shadow-sm shadow-emerald-400"></span>
            <span class="text-slate-300 font-medium">Equity (Account Capital)</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-3 h-1 bg-slate-500 inline-block"></span>
            <span>Peak High-Water Mark</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-2.5 h-2.5 rounded-full bg-emerald-500/30 border border-emerald-400 inline-block"></span>
            <span>Winning Trade</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-2.5 h-2.5 rounded-full bg-rose-500/30 border border-rose-400 inline-block"></span>
            <span>Losing Trade</span>
          </div>
        </div>
        <div class="mono text-slate-500">
          Base: ₹10,00,000.00 → Peak: ₹11,57,384.14
        </div>
      </div>
    </section>

    <!-- Strategy Rulebook & Insights Grid -->
    <section class="grid grid-cols-1 lg:grid-cols-3 gap-6">

      <!-- Column 1 & 2: Strategy Blueprint -->
      <div class="lg:col-span-2 bg-slate-900/90 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-6">
        <div class="flex items-center justify-between border-b border-slate-800 pb-4">
          <div class="flex items-center gap-2.5">
            <span class="text-xl">📐</span>
            <h3 class="font-bold text-white text-base">Strategy Rulebook & Implementation Reference</h3>
          </div>
          <span class="text-xs px-2.5 py-1 rounded-lg bg-teal-500/10 text-teal-400 border border-teal-500/20 font-medium">
            Systematic Rules
          </span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <!-- Step 1 -->
          <div class="bg-slate-950/60 border border-slate-800/90 rounded-2xl p-4 space-y-2">
            <div class="flex items-center gap-2 text-emerald-400 font-semibold">
              <span class="w-5 h-5 rounded-md bg-emerald-500/20 flex items-center justify-center text-xs">1</span>
              <span>The Setup (09:15 – 09:30 AM)</span>
            </div>
            <p class="text-slate-300 leading-relaxed">
              Let the first 15-minute candle complete. Mark its high as <span class="text-white font-medium">OR_High</span> and its low as <span class="text-white font-medium">OR_Low</span>. Do not take any trade before 09:30 AM.
            </p>
          </div>

          <!-- Step 2 -->
          <div class="bg-slate-950/60 border border-slate-800/90 rounded-2xl p-4 space-y-2">
            <div class="flex items-center gap-2 text-cyan-400 font-semibold">
              <span class="w-5 h-5 rounded-md bg-cyan-500/20 flex items-center justify-center text-xs">2</span>
              <span>The Filter (Do We Trade Today?)</span>
            </div>
            <p class="text-slate-300 leading-relaxed">
              Compare with Yesterday's High (PDH) and Low (PDL). If 1st candle breaks either PDH or PDL, trade today. If it stays <span class="text-amber-400 font-semibold">completely inside</span> yesterday's range: <span class="text-rose-400 font-medium">SKIP DAY</span> (filtered 25 choppy days!).
            </p>
          </div>

          <!-- Step 3 -->
          <div class="bg-slate-950/60 border border-slate-800/90 rounded-2xl p-4 space-y-2">
            <div class="flex items-center gap-2 text-indigo-400 font-semibold">
              <span class="w-5 h-5 rounded-md bg-indigo-500/20 flex items-center justify-center text-xs">3</span>
              <span>The Entry & Pullback (09:30 AM – 01:30 PM)</span>
            </div>
            <p class="text-slate-300 leading-relaxed">
              Wait for a 15-min candle to <span class="text-white font-medium">close</span> outside the range. <span class="text-emerald-400">Bullish:</span> Close &gt; OR_High. <span class="text-rose-400">Bearish:</span> Close &lt; OR_Low. <strong>Don't chase.</strong> Enter only on a <strong>50% pullback</strong> into that breakout candle.
            </p>
          </div>

          <!-- Step 4 -->
          <div class="bg-slate-950/60 border border-slate-800/90 rounded-2xl p-4 space-y-2">
            <div class="flex items-center gap-2 text-violet-400 font-semibold">
              <span class="w-5 h-5 rounded-md bg-violet-500/20 flex items-center justify-center text-xs">4</span>
              <span>Position Sizing (1% Account Risk)</span>
            </div>
            <p class="text-slate-300 leading-relaxed">
              Max risk is strictly 1% of account (<span class="text-emerald-400 font-medium">₹10,000</span> on ₹10 Lakhs). Stop Loss = extreme of breakout candle. Risk $R$ = distance from Entry to SL. Size lots to ensure 1R loss = ₹10,000.
            </p>
          </div>
        </div>

        <!-- Step 5: Targets & Scaling -->
        <div class="bg-gradient-to-r from-slate-950 to-slate-900 border border-slate-800 rounded-2xl p-4 space-y-3 text-xs">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2 text-amber-400 font-bold">
              <span>🎯</span>
              <span>5. Asymmetric Profit Scaling & Trailing Protocol</span>
            </div>
            <span class="text-slate-400">Hard Exit at 2:55 PM</span>
          </div>

          <div class="grid grid-cols-2 sm:grid-cols-5 gap-2 text-center pt-1">
            <div class="p-2.5 rounded-xl bg-slate-900/90 border border-slate-800">
              <div class="font-bold text-emerald-400">+3R Target</div>
              <div class="text-slate-300 text-[11px] mt-0.5">Sell 30% Lots</div>
              <div class="text-amber-400 font-medium text-[10px] mt-1">SL → Breakeven</div>
            </div>
            <div class="p-2.5 rounded-xl bg-slate-900/90 border border-slate-800">
              <div class="font-bold text-emerald-400">+5R Target</div>
              <div class="text-slate-300 text-[11px] mt-0.5">Sell 30% Lots</div>
              <div class="text-emerald-400 font-medium text-[10px] mt-1">SL → +3R</div>
            </div>
            <div class="p-2.5 rounded-xl bg-slate-900/90 border border-slate-800">
              <div class="font-bold text-emerald-400">+8R Target</div>
              <div class="text-slate-300 text-[11px] mt-0.5">Sell 20% Lots</div>
              <div class="text-emerald-400 font-medium text-[10px] mt-1">SL → +5R</div>
            </div>
            <div class="p-2.5 rounded-xl bg-slate-900/90 border border-slate-800">
              <div class="font-bold text-emerald-400">+10R Target</div>
              <div class="text-slate-300 text-[11px] mt-0.5">Sell 10% Lots</div>
              <div class="text-indigo-400 font-medium text-[10px] mt-1">Lock 90% Total</div>
            </div>
            <div class="p-2.5 rounded-xl bg-slate-900/90 border border-slate-800 col-span-2 sm:col-span-1">
              <div class="font-bold text-cyan-400">10% Runner</div>
              <div class="text-slate-300 text-[11px] mt-0.5">Trail 50% Peak</div>
              <div class="text-rose-400 font-medium text-[10px] mt-1">Exit @ 2:55 PM</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Column 3: Market Regime & Filter Funnel -->
      <div class="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 shadow-xl flex flex-col justify-between space-y-6">
        <div>
          <div class="flex items-center justify-between border-b border-slate-800 pb-4">
            <h3 class="font-bold text-white text-base">Day Filter Distribution</h3>
            <span class="text-xs text-slate-400">83 Trading Days</span>
          </div>

          <div class="mt-6 space-y-4">
            <!-- Filter 1: Skipped Inside -->
            <div>
              <div class="flex justify-between text-xs mb-1">
                <span class="text-amber-400 font-medium">🔴 Inside Days Skipped</span>
                <span class="mono text-white font-bold">25 days (30.1%)</span>
              </div>
              <div class="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                <div class="bg-amber-400 h-full rounded-full" style="width: 30.1%;"></div>
              </div>
              <p class="text-[11px] text-slate-400 mt-1">Avoided range-bound chop and false breakouts.</p>
            </div>

            <!-- Filter 2: Filter Passed, No Fill -->
            <div>
              <div class="flex justify-between text-xs mb-1">
                <span class="text-slate-300 font-medium">⚪ No 50% Pullback Fill</span>
                <span class="mono text-white font-bold">23 days (27.7%)</span>
              </div>
              <div class="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                <div class="bg-slate-500 h-full rounded-full" style="width: 27.7%;"></div>
              </div>
              <p class="text-[11px] text-slate-400 mt-1">Prevented chasing extended candles without discounts.</p>
            </div>

            <!-- Filter 3: Traded -->
            <div>
              <div class="flex justify-between text-xs mb-1">
                <span class="text-emerald-400 font-medium">🟢 Executed Setups</span>
                <span class="mono text-white font-bold">35 days (42.2%)</span>
              </div>
              <div class="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                <div class="bg-emerald-400 h-full rounded-full" style="width: 42.2%;"></div>
              </div>
              <p class="text-[11px] text-slate-400 mt-1">Clean breakouts with favorable risk-to-reward entries.</p>
            </div>
          </div>
        </div>

        <!-- Monthly Mini Performance Table -->
        <div class="pt-4 border-t border-slate-800 text-xs">
          <div class="text-slate-400 font-semibold mb-2">Monthly Net Contribution</div>
          <div class="space-y-1.5">
            <div class="flex justify-between items-center py-1 border-b border-slate-800/60">
              <span class="text-slate-300">Jun 2026 (8 trades)</span>
              <span class="mono text-rose-400 font-semibold">-₹42,605</span>
            </div>
            <div class="flex justify-between items-center py-1 border-b border-slate-800/60">
              <span class="text-slate-300">Jul 2026 (10 trades)</span>
              <span class="mono text-emerald-400 font-semibold">+₹27,278</span>
            </div>
            <div class="flex justify-between items-center py-1 border-b border-slate-800/60">
              <span class="text-slate-300">Aug 2026 (8 trades)</span>
              <span class="mono text-rose-400 font-semibold">-₹27,750</span>
            </div>
            <div class="flex justify-between items-center py-1 border-b border-slate-800/60">
              <span class="text-slate-300">Sep 2026 (7 trades)</span>
              <span class="mono text-emerald-400 font-bold">+₹1,14,297</span>
            </div>
            <div class="flex justify-between items-center py-1">
              <span class="text-slate-300">Oct 2026 (2 trades)</span>
              <span class="mono text-emerald-400 font-bold">+₹86,165</span>
            </div>
          </div>
        </div>

      </div>
    </section>

    <!-- Complete Trade Log Table Card -->
    <section class="bg-slate-900/90 border border-slate-800 rounded-3xl p-5 sm:p-7 shadow-xl space-y-4">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 class="text-lg font-bold text-white tracking-tight">Full Executed Trades Log (35 Trades)</h2>
          <p class="text-xs text-slate-400">Search and filter every individual trade executed during the 4-month backtest.</p>
        </div>

        <!-- Filter & Search Controls -->
        <div class="flex flex-wrap items-center gap-2 text-xs">
          <input id="searchInput" type="text" placeholder="Search date, CE/PE, reason..." class="bg-slate-950 border border-slate-700/80 rounded-xl px-3 py-1.5 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500 w-52">
          
          <select id="typeFilter" class="bg-slate-950 border border-slate-700/80 rounded-xl px-3 py-1.5 text-slate-200 focus:outline-none focus:border-emerald-500">
            <option value="ALL">All Types</option>
            <option value="CE">CE (Calls)</option>
            <option value="PE">PE (Puts)</option>
          </select>

          <select id="outcomeFilter" class="bg-slate-950 border border-slate-700/80 rounded-xl px-3 py-1.5 text-slate-200 focus:outline-none focus:border-emerald-500">
            <option value="ALL">All Outcomes</option>
            <option value="WIN">Winners Only</option>
            <option value="LOSS">Losses Only</option>
          </select>
        </div>
      </div>

      <!-- Table Container -->
      <div class="overflow-x-auto custom-scrollbar rounded-2xl border border-slate-800/80">
        <table class="w-full text-left text-xs whitespace-nowrap">
          <thead class="bg-slate-950/80 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
            <tr>
              <th class="py-3 px-4">#</th>
              <th class="py-3 px-4">Date</th>
              <th class="py-3 px-4">Type</th>
              <th class="py-3 px-4">Filter Trigger</th>
              <th class="py-3 px-4">Risk (Pts)</th>
              <th class="py-3 px-4">Lots</th>
              <th class="py-3 px-4">Net P&L (₹)</th>
              <th class="py-3 px-4">Capital After</th>
              <th class="py-3 px-4">Target Progression / Exit Reasoning</th>
            </tr>
          </thead>
          <tbody id="tradeTableBody" class="divide-y divide-slate-800/60 bg-slate-900/40 font-normal">
            <!-- Populated via Javascript -->
          </tbody>
        </table>
      </div>
      
      <div class="text-right text-xs text-slate-500 pt-2">
        Showing <span id="filteredCount" class="font-semibold text-slate-300">35</span> of 35 recorded trades.
      </div>
    </section>

  </main>

  <!-- Embedded Dataset & Interactive Script -->
  <script>
    const rawData = {json_payload};
    const trades = rawData.trades;

    // Filter controls
    let currentFilterView = 'ALL';
    const searchInput = document.getElementById('searchInput');
    const typeFilter = document.getElementById('typeFilter');
    const outcomeFilter = document.getElementById('outcomeFilter');
    const tableBody = document.getElementById('tradeTableBody');
    const filteredCount = document.getElementById('filteredCount');

    function renderTable() {{
      const query = searchInput.value.toLowerCase();
      const typeVal = typeFilter.value;
      const outcomeVal = outcomeFilter.value;

      tableBody.innerHTML = '';
      let matchCount = 0;

      trades.forEach((t, idx) => {{
        const isWin = t.total_pnl > 0;
        const isLoss = t.total_pnl < 0;

        // Check Type
        if (typeVal !== 'ALL' && t.type !== typeVal) return;

        // Check Outcome
        if (outcomeVal === 'WIN' && !isWin) return;
        if (outcomeVal === 'LOSS' && !isLoss) return;

        // Check Search Query
        const legReasons = t.legs.map(l => l.reason).join(' ');
        const rowStr = `${{t.date}} ${{t.type}} ${{t.filter}} ${{legReasons}}`.toLowerCase();
        if (query && !rowStr.includes(query)) return;

        matchCount++;

        const tr = document.createElement('tr');
        tr.className = 'hover:bg-slate-800/40 transition';

        const pnlFormatted = (t.total_pnl >= 0 ? '+' : '') + '₹' + Math.abs(t.total_pnl).toLocaleString('en-IN', {{minimumFractionDigits: 2, maximumFractionDigits: 2}});
        const pnlColorClass = isWin ? 'text-emerald-400 font-bold' : (isLoss ? 'text-rose-400 font-semibold' : 'text-slate-300');
        
        const typeBadge = t.type === 'CE' 
          ? '<span class="px-2 py-0.5 rounded-md font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">CE (Buy)</span>'
          : '<span class="px-2 py-0.5 rounded-md font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">PE (Buy)</span>';

        const legsFormatted = t.legs.map(l => {{
          let bClass = 'bg-slate-800 text-slate-300 border-slate-700';
          if (l.reason.includes('Target 1')) bClass = 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30';
          if (l.reason.includes('Target 2') || l.reason.includes('Target 3')) bClass = 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 font-semibold';
          if (l.reason.includes('Breakeven')) bClass = 'bg-amber-500/10 text-amber-300 border-amber-500/20';
          if (l.reason.includes('Stop Loss')) bClass = 'bg-rose-500/10 text-rose-400 border-rose-500/20';
          return `<span class="inline-block px-2 py-0.5 rounded text-[11px] border ${{bClass}} mr-1 mb-0.5">${{l.reason}} (${{l.lots}}L)</span>`;
        }}).join('');

        tr.innerHTML = `
          <td class="py-3 px-4 mono text-slate-500 font-medium">${{idx + 1}}</td>
          <td class="py-3 px-4 font-semibold text-slate-200">${{t.date}}</td>
          <td class="py-3 px-4">${{typeBadge}}</td>
          <td class="py-3 px-4 text-slate-300">${{t.filter}}</td>
          <td class="py-3 px-4 mono text-slate-300">${{t.risk_points.toFixed(1)}}</td>
          <td class="py-3 px-4 mono text-slate-300">${{t.total_lots}}</td>
          <td class="py-3 px-4 mono ${{pnlColorClass}}">${{pnlFormatted}}</td>
          <td class="py-3 px-4 mono text-slate-300">₹${{t.account_capital.toLocaleString('en-IN')}}</td>
          <td class="py-3 px-4 text-slate-400">${{legsFormatted}}</td>
        `;
        tableBody.appendChild(tr);
      }});

      filteredCount.innerText = matchCount;
    }}

    searchInput.addEventListener('input', renderTable);
    typeFilter.addEventListener('change', renderTable);
    outcomeFilter.addEventListener('change', renderTable);

    // Initial table render
    renderTable();


    // ==========================================
    // CANVAS EQUITY CURVE CHART ENGINE
    // ==========================================
    const canvas = document.getElementById('equityChartCanvas');
    const ctx = canvas.getContext('2d');
    const tooltip = document.getElementById('chartTooltip');

    // Prepare equity points
    const equityData = [
      {{ date: '2026-06-11 (Start)', equity: 1000000.0, pnl: 0, type: 'START', hwm: 1000000.0 }}
    ];
    let runningHwm = 1000000.0;
    trades.forEach(t => {{
      if (t.account_capital > runningHwm) runningHwm = t.account_capital;
      equityData.push({{
        date: t.date,
        equity: t.account_capital,
        pnl: t.total_pnl,
        type: t.type,
        hwm: runningHwm,
        risk: t.risk_points,
        legs: t.legs
      }});
    }});

    function getFilteredEquityData(range) {{
      if (range === 'JUL_AUG') {{
        return equityData.filter(d => d.date.startsWith('2026-07') || d.date.startsWith('2026-08'));
      }} else if (range === 'SEP_OCT') {{
        return equityData.filter(d => d.date.startsWith('2026-09') || d.date.startsWith('2026-10'));
      }}
      return equityData;
    }}

    let activeData = equityData;
    let chartMetrics = {{}};

    function resizeCanvas() {{
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.scale(dpr, dpr);
      chartMetrics.width = rect.width;
      chartMetrics.height = rect.height;
    }}

    function drawChart() {{
      resizeCanvas();
      const width = chartMetrics.width;
      const height = chartMetrics.height;
      ctx.clearRect(0, 0, width, height);

      const padLeft = 70;
      const padRight = 30;
      const padTop = 30;
      const padBottom = 40;

      const plotW = width - padLeft - padRight;
      const plotH = height - padTop - padBottom;

      const equities = activeData.map(d => d.equity);
      const hwms = activeData.map(d => d.hwm);
      const minVal = Math.min(...equities) * 0.99;
      const maxVal = Math.max(...hwms) * 1.01;

      function getX(idx) {{
        return padLeft + (idx / (activeData.length - 1)) * plotW;
      }}
      function getY(val) {{
        return padTop + plotH - ((val - minVal) / (maxVal - minVal)) * plotH;
      }}

      // Horizontal Grid Lines
      ctx.lineWidth = 1;
      ctx.strokeStyle = 'rgba(51, 65, 85, 0.4)';
      const gridSteps = 5;
      ctx.fillStyle = '#64748b';
      ctx.font = '10px JetBrains Mono, monospace';
      ctx.textAlign = 'right';

      for (let s = 0; s <= gridSteps; s++) {{
        const v = minVal + (s / gridSteps) * (maxVal - minVal);
        const y = getY(v);
        ctx.beginPath();
        ctx.moveTo(padLeft, y);
        ctx.lineTo(width - padRight, y);
        ctx.stroke();

        ctx.fillText('₹' + (v / 100000).toFixed(2) + 'L', padLeft - 10, y + 3);
      }}

      // Draw Base Capital Reference Line (₹10,00,000)
      const base10L = 1000000.0;
      if (base10L >= minVal && base10L <= maxVal) {{
        const yBase = getY(base10L);
        ctx.setLineDash([4, 4]);
        ctx.strokeStyle = 'rgba(148, 163, 184, 0.4)';
        ctx.beginPath();
        ctx.moveTo(padLeft, yBase);
        ctx.lineTo(width - padRight, yBase);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = '#94a3b8';
        ctx.fillText('Initial ₹10L', width - padRight - 5, yBase - 6);
      }}

      // High-Water Mark Line (Step Line)
      ctx.lineWidth = 1.5;
      ctx.strokeStyle = '#475569';
      ctx.beginPath();
      for (let i = 0; i < activeData.length; i++) {{
        const x = getX(i);
        const y = getY(activeData[i].hwm);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }}
      ctx.stroke();

      // Area Fill Under Equity Curve
      const grad = ctx.createLinearGradient(0, padTop, 0, padTop + plotH);
      grad.addColorStop(0, 'rgba(16, 185, 129, 0.28)');
      grad.addColorStop(1, 'rgba(16, 185, 129, 0.0)');

      ctx.beginPath();
      ctx.moveTo(getX(0), getY(activeData[0].equity));
      for (let i = 1; i < activeData.length; i++) {{
        ctx.lineTo(getX(i), getY(activeData[i].equity));
      }}
      ctx.lineTo(getX(activeData.length - 1), padTop + plotH);
      ctx.lineTo(getX(0), padTop + plotH);
      ctx.closePath();
      ctx.fillStyle = grad;
      ctx.fill();

      // Main Equity Curve Line
      ctx.lineWidth = 2.5;
      ctx.strokeStyle = '#10b981'; // Emerald
      ctx.beginPath();
      for (let i = 0; i < activeData.length; i++) {{
        const x = getX(i);
        const y = getY(activeData[i].equity);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }}
      ctx.stroke();

      // Plot Trade Points
      for (let i = 0; i < activeData.length; i++) {{
        const d = activeData[i];
        const x = getX(i);
        const y = getY(d.equity);

        if (d.type === 'START') continue;

        ctx.beginPath();
        ctx.arc(x, y, 4, 0, Math.PI * 2);
        if (d.pnl > 0) {{
          ctx.fillStyle = '#10b981';
          ctx.strokeStyle = '#022c22';
        }} else {{
          ctx.fillStyle = '#f43f5e';
          ctx.strokeStyle = '#4c0519';
        }}
        ctx.lineWidth = 1.5;
        ctx.fill();
        ctx.stroke();
      }}

      // X-Axis Date Labels
      ctx.fillStyle = '#64748b';
      ctx.font = '10px JetBrains Mono, monospace';
      ctx.textAlign = 'center';
      const labelInterval = Math.max(1, Math.floor(activeData.length / 7));
      for (let i = 0; i < activeData.length; i += labelInterval) {{
        const x = getX(i);
        const dStr = activeData[i].date.slice(5, 10);
        ctx.fillText(dStr, x, padTop + plotH + 20);
      }}

      chartMetrics.getX = getX;
      chartMetrics.getY = getY;
      chartMetrics.padLeft = padLeft;
      chartMetrics.padRight = padRight;
      chartMetrics.padTop = padTop;
      chartMetrics.plotW = plotW;
      chartMetrics.plotH = plotH;
    }}

    function renderChart(range) {{
      activeData = getFilteredEquityData(range);
      currentFilterView = range;

      // Update button active state
      ['viewAllBtn', 'viewQ3Btn', 'viewQ4Btn'].forEach(id => {{
        const b = document.getElementById(id);
        b.className = 'px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition';
      }});
      if (range === 'ALL') document.getElementById('viewAllBtn').className = 'px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-500 text-slate-950 transition';
      if (range === 'JUL_AUG') document.getElementById('viewQ3Btn').className = 'px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-500 text-slate-950 transition';
      if (range === 'SEP_OCT') document.getElementById('viewQ4Btn').className = 'px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-500 text-slate-950 transition';

      drawChart();
    }}

    // Canvas Hover Interactivity
    canvas.addEventListener('mousemove', (e) => {{
      const rect = canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      if (!chartMetrics.getX) return;

      let closestIdx = -1;
      let minDistance = 9999;

      activeData.forEach((d, idx) => {{
        const x = chartMetrics.getX(idx);
        const dist = Math.abs(x - mouseX);
        if (dist < minDistance) {{
          minDistance = dist;
          closestIdx = idx;
        }}
      }});

      if (closestIdx !== -1 && minDistance < 40) {{
        const point = activeData[closestIdx];
        const px = chartMetrics.getX(closestIdx);
        const py = chartMetrics.getY(point.equity);

        tooltip.style.left = `${{Math.min(rect.width - 220, Math.max(10, px - 100))}}px`;
        tooltip.style.top = `${{Math.max(10, py - 95)}}px`;
        tooltip.classList.remove('hidden');

        const pnlStr = point.type === 'START' ? 'Initial Capital' : ((point.pnl >= 0 ? '+' : '') + '₹' + point.pnl.toLocaleString('en-IN', {{minimumFractionDigits: 2}}));
        const pnlColor = point.pnl > 0 ? 'text-emerald-400' : (point.pnl < 0 ? 'text-rose-400' : 'text-slate-300');

        tooltip.innerHTML = `
          <div class="font-bold text-white flex justify-between items-center pb-1 border-b border-slate-800">
            <span>${{point.date}}</span>
            <span class="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">${{point.type}}</span>
          </div>
          <div class="pt-1.5 space-y-1">
            <div class="flex justify-between">
              <span class="text-slate-400">Equity:</span>
              <span class="mono font-bold text-white">₹${{point.equity.toLocaleString('en-IN', {{minimumFractionDigits: 2}})}}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-400">Trade P&L:</span>
              <span class="mono font-bold ${{pnlColor}}">${{pnlStr}}</span>
            </div>
            <div class="flex justify-between text-[11px]">
              <span class="text-slate-500">High-Water Mark:</span>
              <span class="mono text-slate-400">₹${{point.hwm.toLocaleString('en-IN')}}</span>
            </div>
          </div>
        `;
      }} else {{
        tooltip.classList.add('hidden');
      }}
    }});

    canvas.addEventListener('mouseleave', () => {{
      tooltip.classList.add('hidden');
    }});

    window.addEventListener('resize', drawChart);
    window.addEventListener('load', () => {{
      renderChart('ALL');
    }});
  </script>
</body>
</html>
"""

# Write to workspace
workspace_target = "/Users/rahul/Documents/Arrow_Algo_trader/equity_curve.html"
with open(workspace_target, "w") as f:
    f.write(html_content)

# Write to artifact directory
artifact_target = "/Users/rahul/.gemini/antigravity/brain/e06732d3-fc7b-4048-8add-85cca4ef6927/equity_curve.html"
with open(artifact_target, "w") as f:
    f.write(html_content)

print("Dashboard generated successfully at:")
print(f"1. {workspace_target}")
print(f"2. {artifact_target}")
