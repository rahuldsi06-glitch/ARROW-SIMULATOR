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
    US_FUTURES_SYMBOLS,
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

    def test_futures_trade_recording_long_and_short(self):
        # 1. Reset account
        self.client.post("/api/game/reset-account", json={"starting_balance": 1000000.0})

        # 2. Record Long Futures trade on NIFTY (+50 pts on 2 lots = 50 * 50 = ₹2,500)
        fut_long_trade = {
            "trade_id": "FUT-L001",
            "symbol": "NIFTY",
            "instrument_type": "futures",
            "strike": 0.0,
            "option_type": "FUT_LONG",
            "expiry_type": "monthly",
            "lot_size": 25,
            "lots": 2,
            "quantity": 50,
            "entry_bar": 5,
            "exit_bar": 15,
            "entry_time": "09:40",
            "exit_time": "10:30",
            "entry_price": 24000.0,
            "exit_price": 24050.0,
            "target_price": 24050.0,
            "stop_loss_price": 23920.0,
            "pnl": 2500.0,
            "pnl_pct": 1.67,
            "exit_reason": "TARGET_HIT"
        }
        res_long = self.client.post("/api/game/trade", json=fut_long_trade)
        self.assertEqual(res_long.status_code, 200)
        data_long = res_long.json()
        self.assertEqual(data_long["new_balance"], 1002500.0)

        # 3. Record Short Futures trade on BANKNIFTY (+120 pts on 1 lot = 120 * 15 = ₹1,800)
        fut_short_trade = {
            "trade_id": "FUT-S001",
            "symbol": "BANKNIFTY",
            "instrument_type": "futures",
            "strike": 0.0,
            "option_type": "FUT_SHORT",
            "expiry_type": "monthly",
            "lot_size": 15,
            "lots": 1,
            "quantity": 15,
            "entry_bar": 20,
            "exit_bar": 30,
            "entry_time": "11:00",
            "exit_time": "11:50",
            "entry_price": 51500.0,
            "exit_price": 51380.0,
            "target_price": 51380.0,
            "stop_loss_price": 51650.0,
            "pnl": 1800.0,
            "pnl_pct": 1.86,
            "exit_reason": "TARGET_HIT"
        }
        res_short = self.client.post("/api/game/trade", json=fut_short_trade)
        self.assertEqual(res_short.status_code, 200)
        data_short = res_short.json()
        self.assertEqual(data_short["new_balance"], 1004300.0)
        self.assertEqual(data_short["state"]["trades_count"], 2)

    def test_us_futures_config_and_instruments(self):
        # 1. Verify MES (Micro S&P 500)
        mes = get_instrument_config("MES")
        self.assertEqual(mes["symbol"], "MES")
        self.assertEqual(mes["market"], "US")
        self.assertEqual(mes["currency"], "USD")
        self.assertEqual(mes["currency_symbol"], "$")
        self.assertEqual(mes["point_value"], 5.0)
        self.assertEqual(mes["tick_size"], 0.25)
        self.assertEqual(mes["margin_per_contract"], 50.0)

        # 2. Verify MNQ (Micro Nasdaq-100)
        mnq = get_instrument_config("MNQ")
        self.assertEqual(mnq["symbol"], "MNQ")
        self.assertEqual(mnq["point_value"], 2.0)
        self.assertEqual(mnq["tick_size"], 0.25)
        self.assertEqual(mnq["margin_per_contract"], 50.0)

        # 3. Verify ES & NQ minis
        es = get_instrument_config("ES")
        nq = get_instrument_config("NQ")
        self.assertEqual(es["point_value"], 50.0)
        self.assertEqual(nq["point_value"], 20.0)

    def test_us_futures_session_creation(self):
        # Create session in US mode
        res = self.client.post("/api/game/session", json={
            "mode": "us_futures",
            "market": "US",
            "symbol": "MES"
        })
        self.assertEqual(res.status_code, 200)
        sess = res.json()["session"]
        self.assertEqual(sess["symbol"], "MES")
        self.assertEqual(sess["market"], "US")
        self.assertEqual(sess["currency"], "USD")
        self.assertEqual(sess["currency_symbol"], "$")
        self.assertEqual(sess["point_value"], 5.0)
        self.assertEqual(sess["margin_per_contract"], 50.0)
        self.assertEqual(sess["total_bars"], 75)
        self.assertGreater(len(sess["candles"]), 0)

        # Verify initial candle has correct tick rounding (0.25)
        first_candle = sess["initial_candle"]
        remainder = round((first_candle["close"] * 100) % 25, 2)
        self.assertIn(remainder, [0.0, 25.0])

    def test_us_futures_trade_recording_and_usd_balances(self):
        # 1. Reset US account balance to $50,000
        reset_res = self.client.post("/api/game/reset-account", json={
            "starting_balance": 50000.0,
            "market": "US",
            "currency": "USD"
        })
        self.assertEqual(reset_res.status_code, 200)
        state = reset_res.json()["state"]
        self.assertEqual(state["usd_starting_balance"], 50000.0)
        self.assertEqual(state["usd_current_balance"], 50000.0)

        # 2. Record Long MES trade: Buy 2 contracts @ 5860.00, Sell @ 5870.00 (+10 pts)
        # PnL = 10 pts * $5/pt * 2 contracts = $100.00
        mes_trade = {
            "trade_id": "US-FUT-001",
            "symbol": "MES",
            "market": "US",
            "currency": "USD",
            "instrument_type": "futures",
            "strike": 0.0,
            "option_type": "FUT_LONG",
            "expiry_type": "monthly",
            "lot_size": 1,
            "lots": 2,
            "quantity": 2,
            "entry_bar": 10,
            "exit_bar": 20,
            "entry_time": "10:20",
            "exit_time": "11:10",
            "entry_price": 5860.0,
            "exit_price": 5870.0,
            "target_price": 5870.0,
            "stop_loss_price": 5855.0,
            "pnl": 100.0,
            "pnl_pct": 100.0,  # $100 profit on $100 day margin
            "exit_reason": "TARGET_HIT"
        }
        trade_res = self.client.post("/api/game/trade", json=mes_trade)
        self.assertEqual(trade_res.status_code, 200)
        trade_data = trade_res.json()
        self.assertEqual(trade_data["currency"], "USD")
        self.assertEqual(trade_data["new_balance"], 50100.0)
        self.assertEqual(trade_data["state"]["usd_current_balance"], 50100.0)


if __name__ == "__main__":
    unittest.main()

