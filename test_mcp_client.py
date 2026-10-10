#!/usr/bin/env python3
"""
Test client to verify Arrow Trade MCP Server over JSON-RPC 2.0 stdio.
"""

import subprocess
import json
import sys

def run_test():
    proc = subprocess.Popen(
        ["./.venv/bin/python3", "mcp_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    def send_rpc(msg_id, method, params=None):
        req = {"jsonrpc": "2.0", "id": msg_id, "method": method}
        if params is not None:
            req["params"] = params
        wire = json.dumps(req) + "\n"
        proc.stdin.write(wire)
        proc.stdin.flush()
        line = proc.stdout.readline()
        if not line:
            err = proc.stderr.read()
            raise RuntimeError(f"Server closed connection. Stderr:\n{err}")
        return json.loads(line)

    print("--- 1. Testing initialize ---")
    init_res = send_rpc(1, "initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "test-client", "version": "1.0.0"}
    })
    print("Initialize response server info:", init_res.get("result", {}).get("serverInfo"))
    assert "serverInfo" in init_res.get("result", {}), "Initialize failed"

    # Send notifications/initialized
    proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
    proc.stdin.flush()

    print("\n--- 2. Testing tools/list ---")
    tools_res = send_rpc(2, "tools/list")
    tools = tools_res.get("result", {}).get("tools", [])
    print(f"Discovered {len(tools)} tools:")
    for t in tools:
        print(f"  - {t['name']}: {t['description'][:60]}...")
    assert len(tools) >= 10, "Expected at least 10 tools"

    print("\n--- 3. Testing get_account_funds ---")
    funds_res = send_rpc(3, "tools/call", {"name": "get_account_funds", "arguments": {}})
    content = funds_res.get("result", {}).get("content", [{}])[0].get("text", "")
    print("Funds result:", content[:200] + "...")
    assert not funds_res.get("result", {}).get("isError", False)

    print("\n--- 4. Testing get_historical_candles (RELIANCE, 10 days) ---")
    candles_res = send_rpc(4, "tools/call", {
        "name": "get_historical_candles",
        "arguments": {"symbol": "RELIANCE", "interval": "day", "days_back": 10}
    })
    c_content = candles_res.get("result", {}).get("content", [{}])[0].get("text", "")
    print("Candles response snippet:\n", c_content[:300] + "...")
    assert "Candles" in c_content or "Open" in c_content or "candles" in c_content.lower()

    print("\n--- 5. Testing calculate_technical_indicators (TCS) ---")
    ind_res = send_rpc(5, "tools/call", {
        "name": "calculate_technical_indicators",
        "arguments": {"symbol": "TCS", "interval": "day", "days_back": 60}
    })
    ind_content = ind_res.get("result", {}).get("content", [{}])[0].get("text", "")
    print("Indicators response snippet:\n", ind_content[:300] + "...")

    print("\n--- 6. Testing backtest_strategy (SMA Crossover on RELIANCE) ---")
    bt_res = send_rpc(6, "tools/call", {
        "name": "backtest_strategy",
        "arguments": {
            "symbol": "RELIANCE",
            "strategy": "sma_crossover",
            "parameters": {"fast_period": 5, "slow_period": 15},
            "interval": "day",
            "days_back": 90,
            "capital": 100000.0
        }
    })
    bt_content = bt_res.get("result", {}).get("content", [{}])[0].get("text", "")
    print("Backtest response snippet:\n", bt_content[:400] + "...")
    assert "performance" in bt_content or "strategy" in bt_content

    print("\n--- 7. Testing backtest_strategy (RSI on INFY) ---")
    rsi_res = send_rpc(7, "tools/call", {
        "name": "backtest_strategy",
        "arguments": {
            "symbol": "INFY",
            "strategy": "rsi",
            "parameters": {"period": 14, "oversold": 30, "overbought": 70},
            "interval": "day",
            "days_back": 90,
            "capital": 50000.0
        }
    })
    rsi_content = rsi_res.get("result", {}).get("content", [{}])[0].get("text", "")
    print("RSI Backtest snippet:\n", rsi_content[:300] + "...")

    print("\n--- 8. Testing get_market_quote (HDFCBANK) ---")
    quote_res = send_rpc(8, "tools/call", {
        "name": "get_market_quote",
        "arguments": {"symbol": "HDFCBANK"}
    })
    quote_content = quote_res.get("result", {}).get("content", [{}])[0].get("text", "")
    print("Market quote snippet:\n", quote_content[:300] + "...")

    proc.terminate()
    print("\nALL MCP TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_test()
