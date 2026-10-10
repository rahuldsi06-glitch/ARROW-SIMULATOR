# Arrow Trade Broker Workspace Instructions & Rules

Whenever interacting with or running tasks for the **Arrow Trade broker** (`arrow.trade` by iRage Broking Services LLP), follow these mandatory rules:

1. **Use the Arrow Trade MCP Server**:
   - For all operations involving historical candle data, strategy backtesting, technical indicator calculation, market quotes, account funds, positions, holdings, margin calculations, and order management, **ALWAYS use the Arrow Trade MCP Server**.
   - Server file: `/Users/rahul/Documents/Arrow_Algo_trader/mcp_server.py`
   - Python virtualenv: `/Users/rahul/Documents/Arrow_Algo_trader/.venv/bin/python3`

2. **If MCP Tools Are Not Connected / Server Is Not Running**:
   - The MCP server is configured in global `~/.gemini/config/mcp_config.json` under `"arrow-trade"`.
   - If native MCP tools are not yet loaded in the current conversation session or if you need to execute MCP actions, interact with `mcp_server.py` using standard JSON-RPC 2.0 or launch it via:
     ```bash
     ./.venv/bin/python3 mcp_server.py
     ```
   - Alternatively, test and execute tool operations directly using the internal helper or `BacktestEngine` / `arrow_trader` modules.

3. **Key Broker Conventions**:
   - **Prices**: Arrow Trade quotes and candles are natively in **paise** (multiplied by 100). The MCP server and `arrow_trader` modules automatically convert them to **Rupees (₹)** ($\div 100$). Always display and format prices in Rupees.
   - **Symbol Suffixes**: Equity symbols on NSE/BSE require the series suffix `-EQ` (e.g. `RELIANCE-EQ`, `TCS-EQ`, `INFY-EQ`). The MCP server automatically normalizes symbols if the suffix is omitted.
   - **Historical Data**: Historical data API (`https://historical-api.arrow.trade`) is free of charge with Arrow Trade.
