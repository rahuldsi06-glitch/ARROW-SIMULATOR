#!/usr/bin/env python3
import unittest
from fastapi.testclient import TestClient

from arrow_trader.game.options_math import (
    norm_cdf,
    norm_pdf,
    calculate_time_to_expiry,
    black_scholes_price,
    estimate_option_bar_extremes,
    calculate_ema,
    calculate_sma,
    calculate_supertrend,
    calculate_fibonacci_levels
)
from arrow_trader.game.instruments import (
    INSTRUMENTS,
    INDEX_SYMBOLS,
    STOCK_SYMBOLS,
    get_instrument_config
)
from arrow_trader.game.simulator_service import SimulatorService
from arrow_trader.web.app import app


class TestGameOptionsMath(unittest.TestCase):
    def test_norm_cdf_and_pdf(self):
        self.assertAlmostEqual(norm_cdf(0.0), 0.5, places=4)
        self.assertAlmostEqual(norm_cdf(1.96), 0.975, places=2)
        self.assertAlmostEqual(norm_cdf(-1.96), 0.025, places=2)
        self.assertAlmostEqual(norm_pdf(0.0), 0.3989, places=3)

    def test_time_to_expiry(self):
        t_weekly_open = calculate_time_to_expiry(0, total_bars=75, expiry_type="weekly")
        t_weekly_close = calculate_time_to_expiry(74, total_bars=75, expiry_type="weekly")
        # Time to expiry should decay as day progresses
        self.assertGreater(t_weekly_open, t_weekly_close)

        t_monthly = calculate_time_to_expiry(0, total_bars=75, expiry_type="monthly")
        self.assertGreater(t_monthly, t_weekly_open)

    def test_black_scholes_pricing(self):
        spot = 23000
        strike = 23000
        T = 3.0 / 252.0  # 3 days
        iv = 0.15

        ce = black_scholes_price(spot, strike, T, iv=iv, option_type="CE")
        pe = black_scholes_price(spot, strike, T, iv=iv, option_type="PE")

        self.assertGreater(ce["price"], 50.0)
        self.assertGreater(pe["price"], 50.0)
        self.assertGreater(ce["delta"], 0.45)
        self.assertLess(ce["delta"], 0.58)
        self.assertLess(pe["delta"], -0.42)
        self.assertGreater(pe["delta"], -0.58)
        self.assertLess(ce["theta"], 0.0)  # Theta decay is negative for long options

    def test_bar_extremes(self):
        extremes = estimate_option_bar_extremes(
            candle_open=23000,
            candle_high=23100,
            candle_low=22950,
            candle_close=23050,
            strike=23000,
            t_years=0.01,
            option_type="CE"
        )
        self.assertGreaterEqual(extremes["high"], extremes["close"])
        self.assertLessEqual(extremes["low"], extremes["close"])
        self.assertGreater(extremes["high"], extremes["low"])

    def test_ema_and_sma_indicators(self):
        series = [100.0 + i * 2.0 for i in range(80)]  # linear uptrend
        ema50 = calculate_ema(series, period=50)
        ma200 = calculate_sma(series, period=200)

        self.assertEqual(len(ema50), len(series))
        self.assertEqual(len(ma200), len(series))
        # In a steady uptrend, fast EMA lags current price but grows smoothly
        self.assertGreater(ema50[-1], ema50[0])
        self.assertGreater(ma200[-1], ma200[0])

    def test_supertrend_indicator(self):
        # 20 upward-trending candles followed by 10 downward candles
        candles = []
        price = 1000.0
        for i in range(20):
            price += 10.0
            candles.append({
                "open": price - 5,
                "high": price + 5,
                "low": price - 8,
                "close": price,
            })
        for i in range(10):
            price -= 20.0
            candles.append({
                "open": price + 5,
                "high": price + 8,
                "low": price - 10,
                "close": price,
            })

        st_res = calculate_supertrend(candles, period=10, multiplier=3.0)
        self.assertEqual(len(st_res["supertrend"]), len(candles))
        self.assertEqual(len(st_res["trend"]), len(candles))
        # Initial uptrend should be Bullish (trend = 1)
        self.assertEqual(st_res["trend"][15], 1)
        # Deep plunge at the end should flip to Bearish (trend = -1)
        self.assertEqual(st_res["trend"][-1], -1)

    def test_fibonacci_calculations(self):
        # Swing Low = 23000, Swing High = 24000 (diff = 1000)
        fibs = calculate_fibonacci_levels(23000.0, 24000.0)
        self.assertEqual(fibs["0.000"], 23000.0)
        self.assertEqual(fibs["0.500"], 23500.0)
        self.assertEqual(fibs["0.618"], 23618.0)
        self.assertEqual(fibs["1.000"], 24000.0)
        self.assertEqual(fibs["1.618"], 24618.0)

        # Custom ratios
        custom_fibs = calculate_fibonacci_levels(100.0, 200.0, custom_ratios=[0.705, 0.79])
        self.assertAlmostEqual(custom_fibs["0.705"], 170.5)
        self.assertAlmostEqual(custom_fibs["0.790"], 179.0)


class TestInstrumentsCatalog(unittest.TestCase):
    def test_indices_present(self):
        for idx in ["NIFTY", "SENSEX", "BANKNIFTY"]:
            self.assertIn(idx, INSTRUMENTS)
            cfg = get_instrument_config(idx)
            self.assertEqual(cfg["type"], "index")
            self.assertGreater(cfg["lot_size"], 0)
            self.assertGreater(cfg["strike_step"], 0)

    def test_stocks_present(self):
        for sym in ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN"]:
            self.assertIn(sym, INSTRUMENTS)
            cfg = get_instrument_config(sym)
            self.assertEqual(cfg["type"], "stock")
            self.assertGreater(cfg["lot_size"], 0)


class TestSimulatorService(unittest.TestCase):
    def setUp(self):
        self.sim = SimulatorService()

    def test_trading_dates(self):
        dates = self.sim.get_trading_dates()
        self.assertIsInstance(dates, list)
        self.assertGreater(len(dates), 10)

    def test_option_chain_builder(self):
        chain = self.sim.get_option_chain("NIFTY", 23260.0, bar_index=10, expiry_type="weekly")
        self.assertEqual(chain["atm_strike"], 23250.0)
        self.assertEqual(len(chain["strikes"]), 7)
        atm_row = [s for s in chain["strikes"] if s["is_atm"]][0]
        self.assertAlmostEqual(atm_row["strike"], 23250.0)
        self.assertEqual(atm_row["call"]["label"], "ATM")


class TestFastAPIRoutes(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_game_html_route(self):
        res = self.client.get("/game")
        self.assertEqual(res.status_code, 200)
        self.assertIn("ARROW TRADE PRO", res.text)
        self.assertIn("lightweight-charts", res.text)

    def test_game_config_route(self):
        res = self.client.get("/api/game/config")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("indices", data)
        self.assertIn("stocks", data)

    def test_option_chain_api(self):
        res = self.client.post("/api/game/option-chain", json={
            "symbol": "NIFTY",
            "spot_price": 23400.0,
            "bar_index": 5,
            "expiry_type": "weekly"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["chain"]["atm_strike"], 23400.0)

    def test_trade_lifecycle_and_reset(self):
        # 1. Reset account to ₹1,00,000
        res = self.client.post("/api/game/reset-account", json={"starting_balance": 100000.0})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["state"]["current_balance"], 100000.0)

        # 2. Record a profitable trade (+₹2,500)
        trade_payload = {
            "trade_id": "TEST-001",
            "symbol": "NIFTY",
            "strike": 23400.0,
            "option_type": "CE",
            "expiry_type": "weekly",
            "lot_size": 25,
            "lots": 2,
            "quantity": 50,
            "entry_bar": 5,
            "exit_bar": 12,
            "entry_time": "09:40",
            "exit_time": "10:15",
            "entry_price": 120.0,
            "exit_price": 170.0,
            "target_price": 170.0,
            "stop_loss_price": 100.0,
            "pnl": 2500.0,
            "pnl_pct": 41.67,
            "exit_reason": "TARGET_HIT"
        }
        res2 = self.client.post("/api/game/trade", json=trade_payload)
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        self.assertEqual(data2["new_balance"], 102500.0)
        self.assertGreater(data2["xp_gained"], 0)

    def test_capital_persists_across_new_sessions_and_days(self):
        # 1. Reset account explicitly
        self.client.post("/api/game/reset-account", json={"starting_balance": 1000000.0})

        # 2. Complete trade on Day 1 (+15,000)
        self.client.post("/api/game/trade", json={
            "trade_id": "DAY1-T1",
            "symbol": "NIFTY",
            "strike": 23000.0,
            "option_type": "CE",
            "expiry_type": "weekly",
            "lot_size": 25,
            "lots": 4,
            "quantity": 100,
            "entry_bar": 2,
            "exit_bar": 10,
            "entry_time": "09:25",
            "exit_time": "10:05",
            "entry_price": 100.0,
            "exit_price": 250.0,
            "target_price": 250.0,
            "stop_loss_price": 85.0,
            "pnl": 15000.0,
            "pnl_pct": 150.0,
            "exit_reason": "TARGET_HIT"
        })

        # 3. Create Day 2 session (e.g. stock)
        s_res = self.client.post("/api/game/session", json={"mode": "stock", "symbol": "RELIANCE"})
        self.assertEqual(s_res.status_code, 200)

        # 4. Check config/account - capital carried over, starting capital preserved
        cfg = self.client.get("/api/game/config").json()
        self.assertEqual(cfg["state"]["starting_balance"], 1000000.0)
        self.assertEqual(cfg["state"]["current_balance"], 1015000.0)
        self.assertEqual(cfg["state"]["all_time_pnl"], 15000.0)


if __name__ == "__main__":
    unittest.main()

