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
        self.assertIn("RS PROP FIRM SIMULATOR", res.text)
        self.assertIn("klinecharts.min.js", res.text)
        self.assertIn("three.min.js", res.text)
        self.assertIn("chart_engine_v2.js", res.text)
        self.assertIn("auth_profile.js", res.text)
        self.assertIn("htf-chart", res.text)
        self.assertIn("toggle-lvl-pdh", res.text)

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

        # Verify sequential progression via next_after_date produces distinct increasing trading dates
        cur_date = sess["date"]
        dates_seen = [cur_date]
        for _ in range(5):
            r = self.client.post("/api/game/session", json={
                "mode": "us_futures",
                "market": "US",
                "symbol": "MES",
                "next_after_date": cur_date
            })
            self.assertEqual(r.status_code, 200)
            nxt = r.json()["session"]["date"]
            self.assertGreater(nxt, cur_date)
            dates_seen.append(nxt)
            cur_date = nxt
        self.assertEqual(len(set(dates_seen)), 6)

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

    def test_prop_firm_setup(self):
        # Setup Topstep style 50k combine
        res = self.client.post("/api/game/propfirm/setup", json={
            "account_size": 50000.0,
            "drawdown_type": "eod_trailing",
            "max_drawdown_pct": 5.0,
            "daily_loss_limit_enabled": True,
            "daily_loss_limit_pct": 3.0,
            "profit_target_pct": 6.0,
            "min_trading_days": 2
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()["prop_firm"]
        self.assertEqual(data["account_size"], 50000.0)
        self.assertEqual(data["drawdown_type"], "eod_trailing")
        self.assertEqual(data["max_drawdown_amount"], 2500.0)
        self.assertEqual(data["drawdown_floor"], 47500.0)
        self.assertEqual(data["daily_loss_limit_amount"], 1500.0)
        self.assertEqual(data["profit_target_amount"], 3000.0)
        self.assertEqual(data["phase"], "evaluation")
        self.assertEqual(data["status"], "active")

    def test_prop_firm_eod_trailing_with_mdd_across_days(self):
        # 1. Setup $50k EOD trailing challenge ($2.5k MDD)
        self.client.post("/api/game/propfirm/setup", json={
            "account_size": 50000.0,
            "drawdown_type": "eod_trailing",
            "max_drawdown_pct": 5.0,
            "daily_loss_limit_enabled": True,
            "daily_loss_limit_pct": 3.0,
            "profit_target_pct": 6.0,
            "min_trading_days": 2
        })

        # 2. Day 1: +$1,200 profit -> Equity $51,200 -> Trailing floor rises to $48,700 ($51,200 - $2,500)
        d1 = self.client.post("/api/game/propfirm/eod", json={
            "day_pnl": 1200.0,
            "day_index": 1,
            "date": "2026-10-01"
        })
        self.assertEqual(d1.status_code, 200)
        pf1 = d1.json()["prop_firm"]
        self.assertEqual(pf1["current_equity"], 51200.0)
        self.assertEqual(pf1["high_water_mark"], 51200.0)
        self.assertEqual(pf1["drawdown_floor"], 48700.0)  # 51200 - 2500
        self.assertEqual(pf1["trading_days_count"], 1)

        # 3. Day 2: +$1,500 profit -> Equity $52,700 -> Trailing floor trails with MDD ($2,500) to $50,200
        d2 = self.client.post("/api/game/propfirm/eod", json={
            "day_pnl": 1500.0,
            "day_index": 2,
            "date": "2026-10-02"
        })
        self.assertEqual(d2.status_code, 200)
        pf2 = d2.json()["prop_firm"]
        self.assertEqual(pf2["current_equity"], 52700.0)
        self.assertEqual(pf2["high_water_mark"], 52700.0)
        self.assertEqual(pf2["drawdown_floor"], 50200.0)  # 52700 - 2500 = 50200
        self.assertEqual(pf2["trading_days_count"], 2)

        # 4. Day 3: -$500 loss -> Equity drops to $52,200 -> Floor stays ratcheted at $50,200
        d3 = self.client.post("/api/game/propfirm/eod", json={
            "day_pnl": -500.0,
            "day_index": 3,
            "date": "2026-10-03"
        })
        self.assertEqual(d3.status_code, 200)
        pf3 = d3.json()["prop_firm"]
        self.assertEqual(pf3["current_equity"], 52200.0)
        self.assertEqual(pf3["high_water_mark"], 52700.0)
        self.assertEqual(pf3["drawdown_floor"], 50200.0)

        # 5. Day 4: +$2,000 profit -> Equity rises to $54,200 -> Trailing floor trails with MDD to $51,700 ($54,200 - $2,500)
        d4 = self.client.post("/api/game/propfirm/eod", json={
            "day_pnl": 2000.0,
            "day_index": 4,
            "date": "2026-10-04"
        })
        self.assertEqual(d4.status_code, 200)
        pf4 = d4.json()["prop_firm"]
        self.assertEqual(pf4["current_equity"], 54200.0)
        self.assertEqual(pf4["high_water_mark"], 54200.0)
        self.assertEqual(pf4["drawdown_floor"], 51700.0)  # 54200 - 2500 = 51700

    def test_prop_firm_pass_and_funded_activation(self):
        # Setup $50k account with $3,000 target and 2 min days
        self.client.post("/api/game/propfirm/setup", json={
            "account_size": 50000.0,
            "drawdown_type": "eod_trailing",
            "max_drawdown_pct": 5.0,
            "daily_loss_limit_enabled": True,
            "daily_loss_limit_pct": 3.0,
            "profit_target_pct": 6.0,
            "min_trading_days": 2
        })

        # Day 1: +$1,600
        self.client.post("/api/game/propfirm/eod", json={
            "day_pnl": 1600.0,
            "day_index": 1,
            "date": "2026-10-01"
        })

        # Day 2: +$1,500 -> Total profit $3,100 >= $3,000 target across 2 days
        d2 = self.client.post("/api/game/propfirm/eod", json={
            "day_pnl": 1500.0,
            "day_index": 2,
            "date": "2026-10-02"
        })
        self.assertEqual(d2.status_code, 200)
        pf = d2.json()["prop_firm"]
        self.assertEqual(pf["status"], "passed")

        # Promote to Funded Account with 40% consistency rule
        funded_res = self.client.post("/api/game/propfirm/activate-funded", json={
            "consistency_rule_pct": 40.0
        })
        self.assertEqual(funded_res.status_code, 200)
        funded_pf = funded_res.json()["prop_firm"]
        self.assertEqual(funded_pf["phase"], "funded")
        self.assertEqual(funded_pf["current_equity"], 50000.0)
        self.assertEqual(funded_pf["consistency_rule_pct"], 40.0)
        self.assertEqual(funded_pf["drawdown_floor"], 47500.0)

    def test_prop_firm_payout_execution(self):
        # 1. Setup and activate funded account
        self.client.post("/api/game/propfirm/setup", json={
            "account_size": 50000.0,
            "drawdown_type": "eod_trailing",
            "max_drawdown_pct": 5.0,
            "daily_loss_limit_enabled": True,
            "daily_loss_limit_pct": 3.0,
            "profit_target_pct": 6.0,
            "min_trading_days": 1
        })
        self.client.post("/api/game/propfirm/activate-funded", json={
            "consistency_rule_pct": 50.0
        })

        # 2. Add profits in funded account across 2 days: +$2,000 each -> total +$4,000, equity $54,000 (50% consistency satisfied)
        self.client.post("/api/game/propfirm/eod", json={
            "day_pnl": 2000.0,
            "day_index": 1,
            "date": "2026-10-05"
        })
        self.client.post("/api/game/propfirm/eod", json={
            "day_pnl": 2000.0,
            "day_index": 2,
            "date": "2026-10-06"
        })

        # 3. Request valid payout of $2,000
        payout_res = self.client.post("/api/game/propfirm/payout", json={
            "amount": 2000.0
        })
        self.assertEqual(payout_res.status_code, 200)
        payout_data = payout_res.json()["prop_firm"]
        self.assertEqual(payout_data["current_equity"], 52000.0)
        self.assertEqual(payout_data["lifetime_payouts"], 2000.0)
        self.assertEqual(len(payout_data["payout_history"]), 1)

        # 4. Request payout exceeding safety cushion (attempt to withdraw $2,500 when buffer is only $2,000)
        invalid_res = self.client.post("/api/game/propfirm/payout", json={
            "amount": 2500.0
        })
        self.assertEqual(invalid_res.status_code, 400)

    def test_prop_firm_mdd_breach(self):
        # Setup $50k account with 5% MDD ($2,500) -> Floor is $47,500
        self.client.post("/api/game/propfirm/setup", json={
            "account_size": 50000.0,
            "drawdown_type": "static",
            "max_drawdown_pct": 5.0,
            "daily_loss_limit_enabled": True,
            "daily_loss_limit_pct": 3.0,
            "profit_target_pct": 6.0,
            "min_trading_days": 1
        })

        # Day 1: Large loss of -$2,600 -> Equity drops to $47,400 < $47,500 floor
        res = self.client.post("/api/game/propfirm/eod", json={
            "day_pnl": -2600.0,
            "day_index": 1,
            "date": "2026-10-06"
        })
        self.assertEqual(res.status_code, 200)
        pf = res.json()["prop_firm"]
        self.assertEqual(pf["current_equity"], 47400.0)
        self.assertEqual(pf["status"], "failed")
        self.assertIn("Max Drawdown Breached", pf["failure_reason"])


    def test_prop_firm_multi_day_stat_carryforward_and_client_state_preservation(self):
        # 1. Custom $100k account setup (4% MDD, 2.5% DLL, 8% Target, 2 days)
        setup_res = self.client.post("/api/game/propfirm/setup", json={
            "account_size": 100000.0,
            "drawdown_type": "eod_trailing",
            "max_drawdown_pct": 4.0,
            "daily_loss_limit_enabled": True,
            "daily_loss_limit_pct": 2.5,
            "profit_target_pct": 8.0,
            "min_trading_days": 2
        })
        self.assertEqual(setup_res.status_code, 200)
        pf = setup_res.json()["prop_firm"]
        self.assertEqual(pf["account_size"], 100000.0)
        self.assertEqual(pf["max_drawdown_amount"], 4000.0)
        self.assertEqual(pf["daily_loss_limit_amount"], 2500.0)
        self.assertEqual(pf["profit_target_amount"], 8000.0)
        self.assertTrue(pf["daily_loss_limit_enabled"])

        # 2. End of Day 1: +$1,500 profit
        pf["current_equity"] = 101500.0
        d1_res = self.client.post("/api/game/propfirm/eod", json={
            "date": "2026-10-10",
            "day_pnl": 1500.0,
            "trades_count": 2,
            "prop_firm": pf
        })
        self.assertEqual(d1_res.status_code, 200)
        pf1 = d1_res.json()["prop_firm"]

        # Ensure Day 1 stats carried forward and not reset to 50k defaults
        self.assertEqual(pf1["account_size"], 100000.0)
        self.assertEqual(pf1["current_equity"], 101500.0)
        self.assertEqual(pf1["high_water_mark"], 101500.0)
        self.assertEqual(pf1["drawdown_floor"], 97500.0)  # 101500 - 4000
        self.assertEqual(pf1["profit_target_amount"], 8000.0)
        self.assertEqual(pf1["total_pnl"], 1500.0)
        self.assertEqual(pf1["trading_days_count"], 1)
        self.assertTrue(pf1["daily_loss_limit_enabled"])
        self.assertEqual(pf1["daily_loss_limit_amount"], 2500.0)
        self.assertEqual(pf1["day_start_equity"], 101500.0)

        # 3. End of Day 2: +$2,000 profit
        pf1["current_equity"] = 103500.0
        d2_res = self.client.post("/api/game/propfirm/eod", json={
            "date": "2026-10-11",
            "day_pnl": 2000.0,
            "trades_count": 3,
            "prop_firm": pf1
        })
        self.assertEqual(d2_res.status_code, 200)
        pf2 = d2_res.json()["prop_firm"]

        # Ensure Day 2 stats accumulated correctly
        self.assertEqual(pf2["account_size"], 100000.0)
        self.assertEqual(pf2["current_equity"], 103500.0)
        self.assertEqual(pf2["high_water_mark"], 103500.0)
        self.assertEqual(pf2["drawdown_floor"], 99500.0)  # 103500 - 4000
        self.assertEqual(pf2["profit_target_amount"], 8000.0)
        self.assertEqual(pf2["total_pnl"], 3500.0)
        self.assertEqual(pf2["trading_days_count"], 2)
        self.assertTrue(pf2["daily_loss_limit_enabled"])
        self.assertEqual(pf2["daily_loss_limit_amount"], 2500.0)
        self.assertEqual(len(pf2["daily_history"]), 2)
        self.assertEqual(pf2["status"], "active")

        # 4. End of Day 3: +$6,000 profit -> Equity $109,500 -> Floor trails with MDD to $105,500 (> $100k account size!)
        pf2["current_equity"] = 109500.0
        d3_res = self.client.post("/api/game/propfirm/eod", json={
            "date": "2026-10-12",
            "day_pnl": 6000.0,
            "trades_count": 2,
            "prop_firm": pf2
        })
        self.assertEqual(d3_res.status_code, 200)
        pf3 = d3_res.json()["prop_firm"]
        self.assertEqual(pf3["current_equity"], 109500.0)
        self.assertEqual(pf3["high_water_mark"], 109500.0)
        self.assertEqual(pf3["drawdown_floor"], 105500.0)  # 109500 - 4000 = 105500! Continues trailing with MDD!
        self.assertEqual(pf3["total_pnl"], 9500.0)
        self.assertEqual(pf3["trading_days_count"], 3)

    def test_prop_firm_funded_activation_carries_characteristics_and_honors_payout(self):
        # 1. Custom $150k Evaluation (4% MDD = $6k, 2.5% DLL = $3.75k, 6% Target = $9k, 2 days)
        self.client.post("/api/game/propfirm/setup", json={
            "account_size": 150000.0,
            "drawdown_type": "eod_trailing",
            "max_drawdown_pct": 4.0,
            "daily_loss_limit_enabled": True,
            "daily_loss_limit_pct": 2.5,
            "profit_target_pct": 6.0,
            "min_trading_days": 2
        })

        # Day 1: +$5,000
        d1 = self.client.post("/api/game/propfirm/eod", json={
            "date": "2026-10-20",
            "day_pnl": 5000.0,
            "trades_count": 2
        })
        pf1 = d1.json()["prop_firm"]

        # Day 2: +$4,500 -> Total $9,500 >= $9,000 target across 2 days -> Passed!
        d2 = self.client.post("/api/game/propfirm/eod", json={
            "date": "2026-10-21",
            "day_pnl": 4500.0,
            "trades_count": 3
        })
        pf2 = d2.json()["prop_firm"]
        self.assertEqual(pf2["status"], "passed")

        # 2. Activate Funded Account carrying client_prop_firm characteristics and choosing 40% consistency rule & 3% payout target ($4,500)
        act_res = self.client.post("/api/game/propfirm/activate-funded", json={
            "consistency_rule_pct": 40.0,
            "payout_target_pct": 3.0,
            "prop_firm": pf2
        })
        self.assertEqual(act_res.status_code, 200)
        funded = act_res.json()["prop_firm"]

        # Verify all characteristics carried over!
        self.assertEqual(funded["phase"], "funded")
        self.assertEqual(funded["status"], "active")
        self.assertEqual(funded["account_size"], 150000.0)
        self.assertEqual(funded["max_drawdown_pct"], 4.0)
        self.assertEqual(funded["max_drawdown_amount"], 6000.0)
        self.assertTrue(funded["daily_loss_limit_enabled"])
        self.assertEqual(funded["daily_loss_limit_pct"], 2.5)
        self.assertEqual(funded["daily_loss_limit_amount"], 3750.0)
        self.assertEqual(funded["drawdown_type"], "eod_trailing")
        self.assertEqual(funded["consistency_rule_pct"], 40.0)
        self.assertEqual(funded["current_equity"], 150000.0)
        self.assertEqual(funded["drawdown_floor"], 144000.0)  # 150000 - 6000
        self.assertEqual(funded["total_pnl"], 0.0)
        self.assertEqual(funded["trading_days_count"], 0)

        # 3. Trade in Funded Account:
        # Funded Day 1: +$3,000 -> Equity $153,000
        f_d1 = self.client.post("/api/game/propfirm/eod", json={
            "date": "2026-10-22",
            "day_pnl": 3000.0,
            "trades_count": 2,
            "prop_firm": funded
        })
        f_pf1 = f_d1.json()["prop_firm"]
        self.assertEqual(f_pf1["current_equity"], 153000.0)

        # Funded Day 2: +$2,500 -> Total profit $5,500. Best day $3,000 / $5,500 = 54.5% (> 40% consistency)
        f_d2 = self.client.post("/api/game/propfirm/eod", json={
            "date": "2026-10-23",
            "day_pnl": 2500.0,
            "trades_count": 2,
            "prop_firm": f_pf1
        })
        f_pf2 = f_d2.json()["prop_firm"]
        self.assertEqual(f_pf2["current_equity"], 155500.0)

        # Attempt payout while consistency > 40%: Should be rejected
        rej_res = self.client.post("/api/game/propfirm/payout", json={
            "amount": 2000.0,
            "prop_firm": f_pf2
        })
        self.assertEqual(rej_res.status_code, 400)
        self.assertIn("Consistency rule not met", rej_res.json()["detail"])

        # Funded Day 3: +$2,500 -> Total profit $8,000. Best day $3,000 / $8,000 = 37.5% (<= 40% consistency!)
        f_d3 = self.client.post("/api/game/propfirm/eod", json={
            "date": "2026-10-24",
            "day_pnl": 2500.0,
            "trades_count": 2,
            "prop_firm": f_pf2
        })
        f_pf3 = f_d3.json()["prop_firm"]
        self.assertEqual(f_pf3["current_equity"], 158000.0)

        # Now request $3,500 payout (criteria met!) -> Should succeed and be honored
        pay1 = self.client.post("/api/game/propfirm/payout", json={
            "amount": 3500.0,
            "prop_firm": f_pf3
        })
        self.assertEqual(pay1.status_code, 200)
        p_data = pay1.json()["prop_firm"]
        self.assertEqual(p_data["current_equity"], 154500.0)  # 158000 - 3500
        self.assertEqual(p_data["lifetime_payouts"], 3500.0)
        self.assertEqual(len(p_data["payout_history"]), 1)
        self.assertEqual(p_data["payout_history"][0]["amount"], 3500.0)

        # Request second payout of remaining available profit $4,500
        pay2 = self.client.post("/api/game/propfirm/payout", json={
            "amount": 4500.0,
            "prop_firm": p_data
        })
        self.assertEqual(pay2.status_code, 200)
        p2_data = pay2.json()["prop_firm"]
        self.assertEqual(p2_data["current_equity"], 150000.0)  # Reset to base capital
        self.assertEqual(p2_data["lifetime_payouts"], 8000.0)
        self.assertEqual(len(p2_data["payout_history"]), 2)

        # Attempt to withdraw $500 when available profit is 0 -> Rejected
        pay3 = self.client.post("/api/game/propfirm/payout", json={
            "amount": 500.0,
            "prop_firm": p2_data
        })
        self.assertEqual(pay3.status_code, 400)
        self.assertIn("exceeds available funded profit", pay3.json()["detail"])

    def test_session_includes_prior_context_and_liquidity_levels(self):
        for payload in [
            {"mode": "index", "market": "IN", "symbol": "NIFTY"},
            {"mode": "us_futures", "market": "US", "symbol": "MES"},
        ]:
            res = self.client.post("/api/game/session", json=payload)
            self.assertEqual(res.status_code, 200)
            sess = res.json()["session"]
            self.assertIn("prior_candles", sess)
            self.assertIn("session_levels", sess)
            self.assertGreaterEqual(len(sess["prior_candles"]), 150)
            self.assertLess(sess["prior_candles"][-1]["time"], sess["candles"][0]["time"])
            lvls = sess["session_levels"]
            for key in ["pdh", "pdl", "asia_high", "asia_low", "london_high", "london_low", "ny_high", "ny_low"]:
                self.assertIn(key, lvls)
                self.assertIsInstance(lvls[key], float)
            self.assertGreaterEqual(lvls["pdh"], lvls["pdl"])
            self.assertGreaterEqual(lvls["asia_high"], lvls["asia_low"])
            self.assertGreaterEqual(lvls["london_high"], lvls["london_low"])

    def test_auth_signup_login_profile_calendar_and_data_until_yesterday(self):
        from datetime import datetime, timedelta
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        # 1. Verify trading dates include up to yesterday (or latest weekday <= yesterday)
        us_dates = self.client.app.router if False else None
        from arrow_trader.game.simulator_service import SimulatorService
        sim = SimulatorService()
        us_list = sim.get_us_trading_dates()
        in_list = sim.get_trading_dates()
        self.assertTrue(len(us_list) > 200)
        self.assertTrue(len(in_list) > 100)
        self.assertGreaterEqual(us_list[-1], "2026-11-25")
        self.assertGreaterEqual(in_list[-1], "2026-11-25")

        # 2. Signup unique user
        import uuid
        uname = f"trader_{uuid.uuid4().hex[:6]}"
        s_res = self.client.post("/api/game/auth/signup", json={
            "username": uname,
            "email": f"{uname}@example.com",
            "password": "password123",
            "full_name": "Test Trader"
        })
        self.assertEqual(s_res.status_code, 200)
        token = s_res.json()["token"]

        # 3. Login
        l_res = self.client.post("/api/game/auth/login", json={
            "identifier": uname,
            "password": "password123"
        })
        self.assertEqual(l_res.status_code, 200)
        self.assertEqual(l_res.json()["user"]["username"], uname)

        # 4. Record trade with Bearer token and verify Tradeify calendar/profile
        t_res = self.client.post("/api/game/trade", headers={"Authorization": f"Bearer {token}"}, json={
            "trade_id": "t-cal-1",
            "session_date": yesterday,
            "symbol": "MES",
            "market": "US",
            "currency": "USD",
            "instrument_type": "futures",
            "option_type": "LONG",
            "lot_size": 1,
            "lots": 2,
            "quantity": 2,
            "entry_bar": 1,
            "exit_bar": 5,
            "entry_time": "09:35",
            "exit_time": "09:55",
            "entry_price": 5900.0,
            "exit_price": 5910.0,
            "pnl": 100.0,
            "pnl_pct": 100.0,
            "exit_reason": "TARGET_HIT"
        })
        self.assertEqual(t_res.status_code, 200)

        p_res = self.client.get("/api/game/auth/profile", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(p_res.status_code, 200)
        pdata = p_res.json()
        self.assertEqual(pdata["stats"]["total_trades"], 1)
        self.assertEqual(pdata["stats"]["net_pnl"], 100.0)
        self.assertIn(yesterday, pdata["calendar"])
        self.assertEqual(pdata["calendar"][yesterday]["pnl"], 100.0)

    def test_prop_firm_custom_daily_max_loss_and_profit_cap(self):
        res = self.client.post("/api/game/propfirm/setup", json={
            "account_size": 10000.0,
            "drawdown_type": "static",
            "max_drawdown_pct": 5.0,
            "daily_loss_limit_enabled": True,
            "daily_loss_limit_pct": 3.0,
            "daily_loss_limit_amount": 250.0,
            "daily_profit_limit_enabled": True,
            "daily_profit_limit_amount": 400.0,
            "profit_target_pct": 6.0,
            "min_trading_days": 2
        })
        self.assertEqual(res.status_code, 200)
        pf = res.json()["prop_firm"]
        self.assertEqual(pf["account_size"], 10000.0)
        self.assertEqual(pf["drawdown_type"], "static")
        self.assertEqual(pf["daily_loss_limit_amount"], 250.0)
        self.assertTrue(pf["daily_profit_limit_enabled"])
        self.assertEqual(pf["daily_profit_limit_amount"], 400.0)

    def test_sequential_day_progression(self):
        # Start on Thursday 2026-10-01
        r1 = self.client.post("/api/game/session", json={"mode": "us_futures", "market": "US", "symbol": "MES", "date": "2026-10-01"})
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json()["session"]["date"], "2026-10-01")

        # Next day -> Friday 2026-10-02
        r2 = self.client.post("/api/game/session", json={"mode": "us_futures", "market": "US", "symbol": "MES", "next_after_date": "2026-10-01"})
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["session"]["date"], "2026-10-02")

        # Next day -> skips weekend -> Monday 2026-10-05
        r3 = self.client.post("/api/game/session", json={"mode": "us_futures", "market": "US", "symbol": "MES", "next_after_date": "2026-10-02"})
        self.assertEqual(r3.status_code, 200)
        self.assertEqual(r3.json()["session"]["date"], "2026-10-05")

    def test_direct_funded_setup_and_standalone_daily_risk_update(self):
        # 1. Start directly in Funded Account with 30% consistency rule
        res = self.client.post("/api/game/propfirm/setup", json={
            "account_size": 100000.0,
            "start_phase": "funded",
            "consistency_rule_pct": 30.0,
            "drawdown_type": "static",
            "max_drawdown_pct": 5.0
        })
        self.assertEqual(res.status_code, 200)
        pf = res.json()["prop_firm"]
        self.assertEqual(pf["phase"], "funded")
        self.assertEqual(pf["status"], "active")
        self.assertEqual(pf["account_size"], 100000.0)
        self.assertEqual(pf["consistency_rule_pct"], 30.0)
        self.assertEqual(pf["drawdown_floor"], 95000.0)

        # 2. Update Daily Risk Settings independently without resetting Funded account
        dr_res = self.client.post("/api/game/propfirm/daily-risk", json={
            "daily_loss_limit_enabled": True,
            "daily_loss_limit_amount": 400.0,
            "daily_profit_limit_enabled": True,
            "daily_profit_limit_amount": 800.0,
            "prop_firm": pf
        })
        self.assertEqual(dr_res.status_code, 200)
        pf2 = dr_res.json()["prop_firm"]
        self.assertEqual(pf2["phase"], "funded")
        self.assertEqual(pf2["account_size"], 100000.0)
        self.assertEqual(pf2["daily_loss_limit_amount"], 400.0)
        self.assertTrue(pf2["daily_profit_limit_enabled"])
        self.assertEqual(pf2["daily_profit_limit_amount"], 800.0)

    def test_funded_account_payout_target_and_min_days_eligibility(self):
        # Direct Funded $50k with 5% Payout Target ($2,500), 3 Min Trading Days, 50% Consistency
        res = self.client.post("/api/game/propfirm/setup", json={
            "account_size": 50000.0,
            "start_phase": "funded",
            "consistency_rule_pct": 50.0,
            "profit_target_pct": 5.0,
            "min_trading_days": 3,
            "drawdown_type": "static",
            "max_drawdown_pct": 5.0
        })
        self.assertEqual(res.status_code, 200)
        pf = res.json()["prop_firm"]
        self.assertEqual(pf["payout_target_amount"], 2500.0)
        self.assertFalse(pf["payout_eligible"])

        # Day 1: +$1,000 (below target & below min days)
        d1 = self.client.post("/api/game/propfirm/eod", json={"date": "2026-10-01", "day_pnl": 1000.0, "trades_count": 1, "prop_firm": pf}).json()["prop_firm"]
        self.assertFalse(d1["payout_eligible"])
        r1 = self.client.post("/api/game/propfirm/payout", json={"amount": 500.0, "prop_firm": d1})
        self.assertEqual(r1.status_code, 400)
        self.assertIn("Minimum trading days not met", r1.json()["detail"])

        # Day 2: +$1,000 (total +$2,000, still below $2,500 target & 2/3 days)
        d2 = self.client.post("/api/game/propfirm/eod", json={"date": "2026-10-02", "day_pnl": 1000.0, "trades_count": 1, "prop_firm": d1}).json()["prop_firm"]
        self.assertFalse(d2["payout_eligible"])

        # Day 3: +$200 (3/3 days met, but total +$2,200 < $2,500 payout target -> still rejected)
        d3 = self.client.post("/api/game/propfirm/eod", json={"date": "2026-10-03", "day_pnl": 200.0, "trades_count": 1, "prop_firm": d2}).json()["prop_firm"]
        self.assertFalse(d3["payout_eligible"])
        r3 = self.client.post("/api/game/propfirm/payout", json={"amount": 1000.0, "prop_firm": d3})
        self.assertEqual(r3.status_code, 400)
        self.assertIn("Payout target not met", r3.json()["detail"])

        # Day 4: +$800 (total +$3,000 >= $2,500, 4 >= 3 days, max day 1000/3000=33.3% <= 50% -> ELIGIBLE!)
        d4 = self.client.post("/api/game/propfirm/eod", json={"date": "2026-10-04", "day_pnl": 800.0, "trades_count": 1, "prop_firm": d3}).json()["prop_firm"]
        self.assertTrue(d4["payout_eligible"])
        r4 = self.client.post("/api/game/propfirm/payout", json={"amount": 1500.0, "prop_firm": d4})
        self.assertEqual(r4.status_code, 200)
        pf_after = r4.json()["prop_firm"]
        self.assertEqual(pf_after["current_equity"], 51500.0)
        self.assertFalse(pf_after["payout_eligible"])  # $1,500 < $2,500 target for next payout


if __name__ == "__main__":
    unittest.main()

