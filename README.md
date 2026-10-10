# 🎯 Arrow.Trade Algorithmic Trading Interface

A modular Python interface and dashboard for the **Arrow (arrow.trade)** low-latency brokerage trading API by *iRage Broking Services LLP*.

Built with the official `pyarrow-client` SDK, providing both an **interactive terminal CLI** (Rich) and a **real-time Web Dashboard** (FastAPI), with an extensible foundation for building and running algorithmic trading strategies.

---

## ⚡ Features

- **Authentication & Session Management**:
  - Automated TOTP login (`user_id`, `password`, `app_secret`, `totp_secret`).
  - Web OAuth login flow with callback tokens.
  - Direct 24-hour JWT token setting with automatic local caching in `.token_cache.json`.
- **Portfolio & Account Tracking**:
  - Live funds, margin utilization, cash, and collateral.
  - Open positions with real-time P&L calculations.
  - Demat holdings with cost vs. current value.
- **Order Management**:
  - Place Market / Limit / SL orders across NSE, BSE, NFO, BFO.
  - Multi-product support (`MIS`, `CNC`, `NRML`).
  - Pre-trade margin requirement calculation.
  - Modify and Cancel open orders (including cancel-all).
  - Order Book and executed Trade Book.
- **Market Data & Streaming**:
  - Live Quotes (LTP, OHLCV, Full Market Depth).
  - Historical Candle Data (1min to 1month intervals).
  - Real-time WebSocket streaming ticks and order update broadcasts.
- **Algorithmic Trading Framework**:
  - Clean `BaseStrategy` class with `on_start()`, `on_tick()`, `on_order_update()`, `on_stop()`.
  - Paper trading (simulation) and Live broker execution modes.
  - Background `AlgoEngine` for running, monitoring, and stopping multiple concurrent strategies.
- **🎮 Arrow Trade Pro - Options Battle Simulator (New!)**:
  - **Index Play**: Bet on Nifty 50 or BSE Sensex (plus Bank Nifty) across random 5-minute historical opening charts.
  - **Stock Play**: Test price-action skills on high-liquidity F&O stocks (Reliance, TCS, Infosys, HDFC Bank, ICICI Bank, SBI, etc.).
  - **Authentic Black-Scholes Greeks Engine**: Real-time Call/Put pricing with Delta, Gamma, and intraday Theta decay.
  - **TradingView Lightweight Charts**: Smooth 5-minute candlestick chart, volume histogram, moving average overlays (EMA 9, EMA 21, VWAP), on-chart entry, target, and stop-loss price lines, and trade markers.
  - **Replay Control Deck**: Play, pause, step 1 bar forward, timeline scrubber, and speed controls (0.5s, 1s, 2s, fast).
  - **Gamification & Trader HUD**: Customizable starting balance (₹1L, ₹5L, ₹10L), live MTM PnL ticker, Win Rate %, Trader XP & Ranks ("Floor Trader" to "Market Maker Titan"), synthesized Web Audio sound effects, and End-of-Day (EOD) Performance Report Cards.
  - **Blind Mode Practice**: Hide asset names and dates to train unbiased price-action reading.
- **Dual Interfaces**:
  - 🖥️ **Interactive Terminal CLI** (`python cli.py`)
  - 🌐 **Modern Web Dashboard** (`python web_app.py` or `python cli.py serve`)
  - 🎮 **Pro Options Simulator** (`python run_game.py` or visit `http://localhost:8000/game`)

---

## 📁 Project Structure

```text
Arrow_Algo_trader/
├── .env.example             # Template for API credentials & secrets
├── requirements.txt         # Project dependencies
├── cli.py                   # Interactive terminal CLI runner
├── web_app.py               # Web dashboard server runner
├── arrow_trader/
│   ├── config.py            # Credentials and token cache manager
│   ├── client_manager.py    # ArrowClient & ArrowStreams wrapper
│   ├── portfolio.py         # Account limits, positions & holdings
│   ├── orders.py            # Order placement, book & margin calculators
│   ├── market.py            # Quotes, candles, option chain & indices
│   ├── stream.py            # Thread-safe WebSocket tick & order dispatcher
│   ├── algo/                # Algorithmic trading engine
│   │   ├── base.py          # Abstract BaseStrategy class
│   │   ├── manager.py       # Multi-strategy AlgoEngine runner
│   │   └── sample_strategy.py # Ready-to-use Momentum sample strategy
│   └── web/                 # FastAPI Web Interface
│       ├── app.py           # REST & WebSocket API backend
│       └── static/          # Dark-theme UI (index.html, app.js, style.css)
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.9+
- A valid [Arrow Trading account](https://app.arrow.trade)
- App ID & App Secret created in **Profile ➔ Trading API**
- Registered Static IP address (mandatory per SEBI regulatory compliance)

### 2. Environment Setup

Create and activate a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Credentials

Copy the `.env.example` file to `.env`:
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```ini
ARROW_APP_ID=your_app_id
ARROW_APP_SECRET=your_app_secret
ARROW_USER_ID=your_user_id
ARROW_PASSWORD=your_password
ARROW_TOTP_SECRET=your_base32_totp_secret

# Optional: provide a pre-existing 24-hr JWT token directly:
# ARROW_ACCESS_TOKEN=your_token_here
```

---

## 🖥️ Terminal Interface (CLI)

### Interactive Menu
Simply run:
```bash
python cli.py
```
This opens an interactive menu where you can view margins, positions, order books, live quotes, place orders, and manage algos.

### Command-Line Shortcuts

| Action | Command |
|---|---|
| Check Auth Status | `python cli.py status` |
| Automated Login | `python cli.py login` |
| Set JWT Token | `python cli.py token <ACCESS_TOKEN>` |
| View Account Funds | `python cli.py funds` |
| View Positions | `python cli.py positions` |
| View Demat Holdings | `python cli.py holdings` |
| View Today's Orders | `python cli.py orders` |
| Fetch Quote | `python cli.py quote RELIANCE-EQ --exchange NSE` |
| Place Buy Order | `python cli.py buy RELIANCE-EQ 1 2500.0 --product CNC --order-type LIMIT` |
| Place Sell Order | `python cli.py sell RELIANCE-EQ 1 2550.0 --product MIS` |
| Cancel Order | `python cli.py cancel <ORDER_ID>` |
| Live Market Stream | `python cli.py stream 3045,1594` |
| Launch Web UI | `python cli.py serve --port 8000` |

---

## 🌐 Web Dashboard

Launch the web interface:
```bash
python web_app.py
```
Then open your browser at **[http://127.0.0.1:8000](http://127.0.0.1:8000)**.

The Web Dashboard includes:
- **📊 Overview**: Available margin, used margin, quick buy/sell order card with live margin preview.
- **💼 Portfolio**: Real-time open positions, net quantity, average buy price, LTP, and P&L color coding.
- **📝 Orders & Trades**: Active order book with status badges and 1-click cancel button.
- **📈 Market Watch**: Real-time quote lookup with OHLC, LTP, change %, and volume.
- **🤖 Algo Sandbox**: Live monitoring panel for running algorithmic strategies and viewing live execution logs.
- **⚙️ Settings & Auth**: TOTP automated login, manual JWT token insertion, and regulatory notices.

---

## 🤖 Building Custom Algorithmic Strategies

You can build new strategies by subclassing `BaseStrategy` from `arrow_trader.algo`:

```python
from arrow_trader.algo import BaseStrategy

class MyCustomStrategy(BaseStrategy):
    def __init__(self):
        super().__init__(
            name="MyCustomAlgo",
            symbols=["RELIANCE-EQ"],
            tokens=[3045],
            exchange="NSE",
            params={"quantity": 10, "paper_trading": True}
        )

    def on_start(self):
        self.log("Strategy initiated!")

    def on_tick(self, tick):
        # Access tick.ltp, tick.net_change, tick.volume, etc.
        if tick.ltp < 2400:
            if not self.params["paper_trading"]:
                self.buy("RELIANCE-EQ", quantity=10, price=tick.ltp)
            self.log(f"Buy condition met at ₹{tick.ltp}")

    def on_stop(self):
        self.log("Strategy cleanly shut down.")
```

Register your strategy in `arrow_trader/algo/manager.py` or pass it to `AlgoEngine.get_instance().register_strategy(...)`.

---

## 🔌 Arrow Trade Model Context Protocol (MCP) Server

A production-ready [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that exposes Arrow Trade broker capabilities directly to AI agents (Claude Desktop, Cursor, Antigravity, etc.) over standard JSON-RPC 2.0 `stdio`.

### 🛠️ Exposed MCP Tools

| Tool | Description |
| :--- | :--- |
| `get_historical_candles` | Fetch historical OHLCV candle data (1m to 1M) converted to Rupees (₹) with high/low/volume stats. |
| `backtest_strategy` | Run quantitative backtesting of algorithmic strategies (`sma_crossover`, `ema_crossover`, `rsi`, `bollinger_bands`, `breakout`) on historical data with Sharpe ratio, win rate, max drawdown, and trade logs. |
| `calculate_technical_indicators` | Compute RSI-14, SMA-20, SMA-50, MACD, and Bollinger Bands with trend analysis. |
| `get_market_quote` | Fetch real-time market quote (LTP, OHLC, VWAP, 5-level market depth). |
| `get_account_funds` | Fetch usable margin, allocated F&O margin, utilized margin, and cash. |
| `get_open_positions` | Retrieve open intraday and overnight positions with unrealized P&L. |
| `get_demat_holdings` | Inspect Demat equity holdings and portfolio value. |
| `calculate_order_margin` | Calculate required margin before placing an order. |
| `place_order` | Place live Market/Limit/SL orders (`MIS`, `CNC`, `NRML`). |
| `get_order_book` | Fetch today's order book with statuses. |
| `cancel_order` / `cancel_all_orders` | Cancel individual or all open/pending orders. |
| `get_option_chain` | Fetch option chain for indices or equities. |
| `get_index_list` | List supported market indices. |

---

### ⚙️ Connecting to AI Clients

#### 1. Claude Desktop (`claude_desktop_config.json`)
Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "arrow-trade": {
      "command": "/Users/rahul/Documents/Arrow_Algo_trader/.venv/bin/python3",
      "args": ["/Users/rahul/Documents/Arrow_Algo_trader/mcp_server.py"],
      "env": {
        "PYTHONPATH": "/Users/rahul/Documents/Arrow_Algo_trader"
      }
    }
  }
}
```

#### 2. Cursor / Antigravity / Claude Code
Run as an MCP stdio server:
```bash
./.venv/bin/python3 mcp_server.py
```

---

## 🛡️ Regulatory Notice (SEBI Compliance)
Under Indian regulations for algorithmic trading:
- API access requires a registered static IP configured in your Arrow developer profile.
- Access tokens expire after 24 hours and must be refreshed each trading day.
