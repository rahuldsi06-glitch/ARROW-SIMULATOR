# Arrow Trade Broker Agent Instructions

Whenever interacting with or running tasks for the **Arrow Trade broker** (`arrow.trade` by iRage Broking Services LLP), follow these mandatory rules:

1. **Use the Arrow Trade MCP Server**:
   - For all operations involving historical candle data, strategy backtesting, technical indicator calculation, market quotes, account funds, positions, holdings, margin calculations, and order management, **ALWAYS use the Arrow Trade MCP Server**.
   - Server file: `/Users/rahul/Documents/Arrow_Algo_trader/mcp_server.py`
   - Python virtualenv: `/Users/rahul/Documents/Arrow_Algo_trader/.venv/bin/python3`

2. **If MCP Tools Are Not Connected / Server Is Not Running**:
   - The MCP server is registered in global `~/.gemini/config/mcp_config.json` under `"arrow-trade"`.
   - If native MCP tools are not yet loaded in the current session, interact with `mcp_server.py` using standard JSON-RPC 2.0 or launch it via:
     ```bash
     ./.venv/bin/python3 mcp_server.py
     ```
   - Alternatively, execute backtests and tool actions using `arrow_trader.backtest.BacktestEngine` and the underlying services.

3. **Key Broker Conventions**:
   - **Prices**: Arrow Trade quotes and candles are natively in **paise** ($\times 100$). The MCP server and `arrow_trader` modules automatically convert them to **Rupees (₹)** ($\div 100$). Always format prices in Rupees.
   - **Symbol Suffixes**: Equity symbols on NSE/BSE require the series suffix `-EQ` (e.g. `RELIANCE-EQ`, `TCS-EQ`, `INFY-EQ`). The MCP server automatically normalizes symbols if omitted.
   - **Historical Data**: Historical candle data API (`https://historical-api.arrow.trade`) is free of charge with Arrow Trade.
