#!/usr/bin/env python3
import sys
import argparse
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich import box

from arrow_trader import (
    Config,
    ArrowClientManager,
    PortfolioService,
    OrderService,
    MarketService,
    StreamManager,
)
from arrow_trader.algo import AlgoEngine, PriceMomentumStrategy

console = Console()


def print_banner():
    console.print(
        Panel.fit(
            "[bold cyan]🎯 Arrow.Trade Algorithmic Trading Interface[/bold cyan]\n"
            "[dim]Ultra-low latency Brokerage API | iRage Broking Services LLP[/dim]",
            border_style="cyan",
            box=box.ROUNDED,
        )
    )


def cmd_status(args=None):
    manager = ArrowClientManager.get_instance()
    is_auth, user_info, err = manager.is_authenticated()

    table = Table(title="Connection & Auth Status", box=box.ROUNDED)
    table.add_column("Parameter", style="cyan bold")
    table.add_column("Value", style="white")

    table.add_row("App ID", manager.app_id or "[red]Not configured[/red]")
    table.add_row("Root URL", manager.root_url or "https://edge.arrow.trade")
    table.add_row(
        "Session Status",
        "[bold green]✓ Authenticated[/bold green]" if is_auth else f"[bold red]✗ Not Authenticated[/bold red] ({err})",
    )

    if is_auth and user_info:
        table.add_row("User ID", str(user_info.get("userID", user_info.get("client_id", "N/A"))))
        table.add_row("Name", str(user_info.get("name", "N/A")))
        table.add_row("Email", str(user_info.get("email", "N/A")))
        token = manager.client.get_token() if manager.client else ""
        table.add_row("Token (preview)", f"{token[:15]}...{token[-8:]}" if token else "N/A")

    console.print(table)


def cmd_login(args=None):
    console.print("[bold cyan]Automated TOTP Login[/bold cyan]")
    app_id = Config.get_app_id() or Prompt.ask("Enter Arrow App ID")
    user_id = Config.get_user_id() or Prompt.ask("Enter Arrow User ID")
    password = Config.get_password() or Prompt.ask("Enter Arrow Password", password=True)
    app_secret = Config.get_app_secret() or Prompt.ask("Enter Arrow App Secret", password=True)
    totp_secret = Config.get_totp_secret() or Prompt.ask("Enter Arrow TOTP Secret (Base32)", password=True)

    manager = ArrowClientManager.get_instance()
    manager.reconfigure(app_id=app_id, app_secret=app_secret)

    with console.status("[bold green]Authenticating with Arrow Trade via TOTP...[/bold green]"):
        try:
            res = manager.auto_login(
                user_id=user_id,
                password=password,
                app_secret=app_secret,
                totp_secret=totp_secret,
            )
            console.print("[bold green]✓ Successfully logged in![/bold green]")
            console.print(f"Logged in as: [bold cyan]{res.get('name', 'User')}[/bold cyan] ({res.get('userID', user_id)})")
            # Save into .env if requested
            if Confirm.ask("Do you want to save these credentials to .env for future sessions?", default=True):
                Config.save_env_var("ARROW_APP_ID", app_id)
                Config.save_env_var("ARROW_APP_SECRET", app_secret)
                Config.save_env_var("ARROW_USER_ID", user_id)
                Config.save_env_var("ARROW_PASSWORD", password)
                Config.save_env_var("ARROW_TOTP_SECRET", totp_secret)
                console.print("[green]Saved to .env![/green]")
        except Exception as e:
            console.print(f"[bold red]Login failed:[/bold red] {e}")


def cmd_set_token(args):
    token = args.token if hasattr(args, "token") and args.token else Prompt.ask("Enter JWT Access Token")
    manager = ArrowClientManager.get_instance()
    with console.status("[bold green]Verifying and saving token...[/bold green]"):
        try:
            manager.set_token(token)
            console.print("[bold green]✓ Token validated and saved successfully![/bold green]")
            cmd_status()
        except Exception as e:
            console.print(f"[bold red]Failed to set token:[/bold red] {e}")


def cmd_web_login(args=None):
    manager = ArrowClientManager.get_instance()
    login_url = manager.get_login_url()
    console.print(Panel(
        f"[bold cyan]Arrow Web Login[/bold cyan]\n\n"
        f"1. Open this link in your browser:\n[bold underline yellow]{login_url}[/bold underline yellow]\n\n"
        f"2. Log in with your Arrow account.\n"
        f"3. You will be redirected to your callback URL with a [green]request-token[/green] in the address bar.",
        title="Web Authentication Flow",
        box=box.ROUNDED,
    ))
    req_token = Prompt.ask("\nPaste the request-token (or entire redirected URL)")
    if "request-token=" in req_token or "request_token=" in req_token:
        # Extract from URL if full URL was pasted
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(req_token)
        qs = parse_qs(parsed.query)
        req_token = qs.get("request-token", qs.get("request_token", [req_token]))[0]

    with console.status("[bold green]Exchanging request token with Arrow broker...[/bold green]"):
        try:
            res = manager.complete_web_login(request_token=req_token.strip())
            console.print("[bold green]✓ Successfully authenticated![/bold green]")
            console.print(f"Logged in as: [bold cyan]{res.get('name', 'Trader')}[/bold cyan] ({res.get('userID', '')})")
            cmd_status()
        except Exception as e:
            console.print(f"[bold red]Token exchange failed:[/bold red] {e}")


def cmd_exchange_token(args):
    req_token = args.request_token if hasattr(args, "request_token") and args.request_token else Prompt.ask("Enter request-token")
    if "request-token=" in req_token or "request_token=" in req_token:
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(req_token)
        qs = parse_qs(parsed.query)
        req_token = qs.get("request-token", qs.get("request_token", [req_token]))[0]

    manager = ArrowClientManager.get_instance()
    with console.status("[bold green]Exchanging request token...[/bold green]"):
        try:
            res = manager.complete_web_login(request_token=req_token.strip())
            console.print("[bold green]✓ Successfully authenticated![/bold green]")
            console.print(f"Logged in as: [bold cyan]{res.get('name', 'Trader')}[/bold cyan] ({res.get('userID', '')})")
            cmd_status()
        except Exception as e:
            console.print(f"[bold red]Token exchange failed:[/bold red] {e}")


def cmd_funds(args=None):
    service = PortfolioService()
    with console.status("[bold cyan]Fetching margins & funds...[/bold cyan]"):
        try:
            limits = service.get_limits()
            table = Table(title="Account Margins & Limits", box=box.ROUNDED)
            table.add_column("Category", style="cyan bold")
            table.add_column("Details", style="white")

            if isinstance(limits, dict):
                for k, v in limits.items():
                    if isinstance(v, dict):
                        sub_text = "\n".join(f"{sk}: ₹{sv:,.2f}" if isinstance(sv, (int, float)) else f"{sk}: {sv}" for sk, sv in v.items())
                        table.add_row(k.upper(), sub_text)
                    else:
                        table.add_row(str(k), f"₹{v:,.2f}" if isinstance(v, (int, float)) else str(v))
            console.print(table)
        except Exception as e:
            console.print(f"[bold red]Error fetching funds:[/bold red] {e}")


def cmd_positions(args=None):
    service = PortfolioService()
    with console.status("[bold cyan]Fetching positions...[/bold cyan]"):
        try:
            positions = service.get_positions()
            if not positions:
                console.print("[yellow]No open positions found.[/yellow]")
                return

            table = Table(title="Open Positions", box=box.ROUNDED)
            table.add_column("Symbol", style="cyan bold")
            table.add_column("Product", style="magenta")
            table.add_column("Net Qty", justify="right")
            table.add_column("Avg Price", justify="right")
            table.add_column("LTP", justify="right")
            table.add_column("P&L", justify="right")

            for pos in positions:
                pnl = float(pos.get("pnl", pos.get("urmtom", 0.0)))
                pnl_style = "green" if pnl >= 0 else "red"
                table.add_row(
                    str(pos.get("symbol", pos.get("tradingSymbol", "N/A"))),
                    str(pos.get("product", "N/A")),
                    str(pos.get("netQty", pos.get("netqty", 0))),
                    f"₹{float(pos.get('buyAvgPrice', pos.get('avgPrice', 0.0))):.2f}",
                    f"₹{float(pos.get('ltp', 0.0)):.2f}",
                    f"[{pnl_style}]₹{pnl:,.2f}[/{pnl_style}]",
                )
            console.print(table)
        except Exception as e:
            console.print(f"[bold red]Error fetching positions:[/bold red] {e}")


def cmd_holdings(args=None):
    service = PortfolioService()
    with console.status("[bold cyan]Fetching holdings...[/bold cyan]"):
        try:
            holdings = service.get_holdings()
            if not holdings:
                console.print("[yellow]No holdings found.[/yellow]")
                return

            table = Table(title="Demat Holdings", box=box.ROUNDED)
            table.add_column("Symbol", style="cyan bold")
            table.add_column("Exchange", style="magenta")
            table.add_column("Total Qty", justify="right")
            table.add_column("Avg Cost", justify="right")
            table.add_column("LTP", justify="right")
            table.add_column("Current Value", justify="right")
            table.add_column("P&L", justify="right")

            for h in holdings:
                qty = int(h.get("quantity", h.get("holdingsQty", 0)))
                cost = float(h.get("averagePrice", h.get("price", 0.0)))
                ltp = float(h.get("ltp", 0.0))
                val = qty * ltp
                pnl = (ltp - cost) * qty if cost > 0 else 0.0
                pnl_style = "green" if pnl >= 0 else "red"

                table.add_row(
                    str(h.get("symbol", h.get("tradingSymbol", "N/A"))),
                    str(h.get("exchange", "NSE")),
                    str(qty),
                    f"₹{cost:.2f}",
                    f"₹{ltp:.2f}",
                    f"₹{val:,.2f}",
                    f"[{pnl_style}]₹{pnl:,.2f}[/{pnl_style}]",
                )
            console.print(table)
        except Exception as e:
            console.print(f"[bold red]Error fetching holdings:[/bold red] {e}")


def cmd_orders(args=None):
    service = OrderService()
    with console.status("[bold cyan]Fetching order book...[/bold cyan]"):
        try:
            orders = service.get_order_book()
            if not orders:
                console.print("[yellow]No orders placed today.[/yellow]")
                return

            table = Table(title="Today's Order Book", box=box.ROUNDED)
            table.add_column("Order ID", style="dim")
            table.add_column("Time", style="dim")
            table.add_column("Symbol", style="cyan bold")
            table.add_column("Side", justify="center")
            table.add_column("Type")
            table.add_column("Qty", justify="right")
            table.add_column("Price", justify="right")
            table.add_column("Status", justify="center")

            for o in orders:
                side = str(o.get("transactionType", o.get("transType", ""))).upper()
                side_style = "[bold green]BUY[/bold green]" if side in ("B", "BUY") else "[bold red]SELL[/bold red]"
                status = str(o.get("status", o.get("orderStatus", "UNKNOWN"))).upper()
                if status in ("COMPLETE", "FILLED", "EXECUTED"):
                    stat_style = "[green]COMPLETE[/green]"
                elif status in ("REJECTED", "CANCELLED"):
                    stat_style = f"[red]{status}[/red]"
                else:
                    stat_style = f"[yellow]{status}[/yellow]"

                table.add_row(
                    str(o.get("orderNo", o.get("orderId", "N/A"))),
                    str(o.get("orderDateTime", o.get("time", "N/A"))),
                    str(o.get("symbol", o.get("tradingSymbol", "N/A"))),
                    side_style,
                    str(o.get("orderType", "LIMIT")),
                    f"{o.get('filledQuantity', 0)}/{o.get('quantity', 0)}",
                    f"₹{float(o.get('price', 0.0)):.2f}",
                    stat_style,
                )
            console.print(table)
        except Exception as e:
            console.print(f"[bold red]Error fetching orders:[/bold red] {e}")


def cmd_quote(args):
    service = MarketService()
    symbol = args.symbol.strip().upper()
    exchange = getattr(args, "exchange", "NSE")
    with console.status(f"[bold cyan]Fetching quote for {symbol} on {exchange}...[/bold cyan]"):
        try:
            quote = service.get_quote(symbol=symbol, exchange=exchange, mode="FULL")
            table = Table(title=f"Market Quote: {symbol} ({exchange})", box=box.ROUNDED)
            table.add_column("Field", style="cyan bold")
            table.add_column("Value", style="white")

            # Arrow quote prices are in paise
            ltp = float(quote.get("ltp", 0.0)) / 100.0
            open_p = float(quote.get("open", 0.0)) / 100.0
            high_p = float(quote.get("high", 0.0)) / 100.0
            low_p = float(quote.get("low", 0.0)) / 100.0
            close_p = float(quote.get("close", 0.0)) / 100.0
            avg_p = float(quote.get("avgPrice", quote.get("avg_price", 0.0))) / 100.0
            change = float(quote.get("net_change", quote.get("netChange", 0.0)))
            chg_style = "green" if change >= 0 else "red"

            table.add_row("LTP", f"₹{ltp:,.2f}")
            table.add_row("Change", f"[{chg_style}]{change:+.2f}%[/{chg_style}]")
            table.add_row("Open", f"₹{open_p:,.2f}")
            table.add_row("High", f"₹{high_p:,.2f}")
            table.add_row("Low", f"₹{low_p:,.2f}")
            table.add_row("Close", f"₹{close_p:,.2f}")
            table.add_row("Volume", f"{int(quote.get('volume', 0)):,}")
            table.add_row("Avg Price (VWAP)", f"₹{avg_p:,.2f}")

            console.print(table)
        except Exception as e:
            console.print(f"[bold red]Error fetching quote:[/bold red] {e}")


def cmd_place_order(args, transaction_type="BUY"):
    service = OrderService()
    symbol = args.symbol.strip().upper()
    qty = int(args.qty)
    price = float(args.price)
    order_type = getattr(args, "order_type", "LIMIT")
    product = getattr(args, "product", "CNC")
    exchange = getattr(args, "exchange", "NSE")

    console.print(
        Panel(
            f"[bold cyan]Order Preview:[/bold cyan]\n"
            f"Action: [{'green' if transaction_type == 'BUY' else 'red'}]{transaction_type}[/]\n"
            f"Symbol: [bold]{symbol}[/bold] ({exchange})\n"
            f"Quantity: [bold]{qty}[/bold]\n"
            f"Price: [bold]₹{price:.2f}[/bold]\n"
            f"Order Type: {order_type} | Product: {product}",
            title="Confirm Order",
            box=box.ROUNDED,
        )
    )

    if not Confirm.ask("Do you want to submit this order to the broker?", default=False):
        console.print("[yellow]Order submission cancelled by user.[/yellow]")
        return

    with console.status("[bold green]Placing order...[/bold green]"):
        try:
            order_id = service.place_order(
                symbol=symbol,
                quantity=qty,
                price=price,
                exchange=exchange,
                transaction_type=transaction_type,
                order_type=order_type,
                product=product,
            )
            console.print(f"[bold green]✓ Order successfully placed! Order ID: {order_id}[/bold green]")
        except Exception as e:
            console.print(f"[bold red]Order placement failed:[/bold red] {e}")


def cmd_cancel(args):
    order_id = str(args.order_id)
    if not Confirm.ask(f"Confirm cancel order {order_id}?", default=True):
        return
    service = OrderService()
    try:
        res = service.cancel_order(order_id)
        console.print(f"[bold green]✓ Cancelled order {order_id}: {res}[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Cancel failed:[/bold red] {e}")


def cmd_stream(args):
    tokens_str = args.tokens
    tokens = [int(t.strip()) for t in tokens_str.split(",") if t.strip().isdigit()]
    if not tokens:
        console.print("[red]Please provide numeric instrument tokens, e.g. 3045,1594[/red]")
        return

    stream_mgr = StreamManager.get_instance()

    def print_tick(tick):
        t = getattr(tick, "token", "N/A")
        ltp = getattr(tick, "ltp", 0.0)
        chg = getattr(tick, "net_change", 0.0)
        c_style = "green" if chg >= 0 else "red"
        console.print(f"[dim]{time.strftime('%H:%M:%S')}[/dim] | Token: [bold cyan]{t}[/bold cyan] | LTP: [bold]₹{ltp:.2f}[/bold] | Change: [{c_style}]{chg:+.2f}%[/{c_style}]")

    stream_mgr.add_tick_listener(print_tick)
    console.print(f"[bold cyan]Subscribing to live ticks for tokens: {tokens}. Press Ctrl+C to stop.[/bold cyan]")
    try:
        stream_mgr.subscribe(tokens)
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping live stream...[/yellow]")
        stream_mgr.remove_tick_listener(print_tick)
        stream_mgr.disconnect()


def cmd_serve(args):
    port = getattr(args, "port", 8000)
    host = getattr(args, "host", "127.0.0.1")
    console.print(f"[bold green]🚀 Launching Arrow Trade Web Dashboard at http://{host}:{port}[/bold green]")
    import uvicorn
    uvicorn.run("arrow_trader.web.app:app", host=host, port=port, reload=False)


def interactive_menu():
    print_banner()
    while True:
        console.print("\n[bold cyan]Select an option:[/bold cyan]")
        console.print("  [1] Connection & Auth Status")
        console.print("  [2] Login via Credentials + TOTP")
        console.print("  [3] Manually Set 24h JWT Token")
        console.print("  [4] Account Funds & Margins")
        console.print("  [5] Open Positions & PnL")
        console.print("  [6] Demat Holdings")
        console.print("  [7] Order Book & Trades")
        console.print("  [8] Fetch Live Quote")
        console.print("  [9] Quick Place Order (Buy/Sell)")
        console.print("  [10] Cancel Order")
        console.print("  [11] Algo Engine & Strategies")
        console.print("  [12] Launch Web Dashboard (Browser)")
        console.print("  [0] Exit")

        choice = Prompt.ask("\nEnter choice", choices=[str(i) for i in range(13)], default="1")

        if choice == "0":
            console.print("[dim]Goodbye![/dim]")
            break
        elif choice == "1":
            cmd_status()
        elif choice == "2":
            cmd_login()
        elif choice == "3":
            cmd_set_token(None)
        elif choice == "4":
            cmd_funds()
        elif choice == "5":
            cmd_positions()
        elif choice == "6":
            cmd_holdings()
        elif choice == "7":
            cmd_orders()
        elif choice == "8":
            sym = Prompt.ask("Enter symbol (e.g. RELIANCE-EQ, NIFTY-INDEX)")
            ex = Prompt.ask("Exchange", choices=["NSE", "BSE", "NFO", "BFO", "INDEX"], default="NSE")
            args = argparse.Namespace(symbol=sym, exchange=ex)
            cmd_quote(args)
        elif choice == "9":
            side = Prompt.ask("Side", choices=["BUY", "SELL"], default="BUY")
            sym = Prompt.ask("Symbol", default="RELIANCE-EQ")
            qty = Prompt.ask("Quantity", default="1")
            price = Prompt.ask("Price", default="0.0")
            ptype = Prompt.ask("Product", choices=["MIS", "CNC", "NRML"], default="MIS")
            otype = Prompt.ask("Order Type", choices=["LIMIT", "MARKET"], default="LIMIT")
            args = argparse.Namespace(
                symbol=sym,
                qty=qty,
                price=price,
                product=ptype,
                order_type=otype,
                exchange="NSE",
            )
            cmd_place_order(args, transaction_type=side)
        elif choice == "10":
            oid = Prompt.ask("Enter Order ID to cancel")
            args = argparse.Namespace(order_id=oid)
            cmd_cancel(args)
        elif choice == "11":
            engine = AlgoEngine.get_instance()
            # Register sample strategy if empty
            if not engine.strategies:
                engine.register_strategy(PriceMomentumStrategy(paper_trading=True))
            strats = engine.get_all_strategies()
            t = Table(title="Algo Strategies", box=box.ROUNDED)
            t.add_column("Name", style="cyan bold")
            t.add_column("Running", style="magenta")
            t.add_column("Symbols")
            t.add_column("Mode")
            for s in strats:
                t.add_row(
                    s["name"],
                    "[green]YES[/green]" if s["is_running"] else "[red]NO[/red]",
                    ", ".join(s["symbols"]),
                    "Paper Trading" if s["params"].get("paper_trading") else "Live",
                )
            console.print(t)
            action = Prompt.ask("Action", choices=["start", "stop", "back"], default="back")
            if action in ("start", "stop"):
                name = Prompt.ask("Strategy name", default=strats[0]["name"] if strats else "")
                if action == "start":
                    engine.start_strategy(name)
                    console.print(f"[green]Started {name}[/green]")
                else:
                    engine.stop_strategy(name)
                    console.print(f"[yellow]Stopped {name}[/yellow]")
        elif choice == "12":
            cmd_serve(argparse.Namespace(host="127.0.0.1", port=8000))


def main():
    parser = argparse.ArgumentParser(description="Arrow.Trade Algorithmic Trading Interface")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("status", help="Show connection and authentication status")
    subparsers.add_parser("login", help="Automated TOTP login")
    subparsers.add_parser("web-login", help="OAuth web browser login flow")

    exchange_parser = subparsers.add_parser("exchange", help="Exchange request-token from callback")
    exchange_parser.add_argument("request_token", nargs="?", help="Request token from callback URL")
    
    token_parser = subparsers.add_parser("token", help="Set access token directly")
    token_parser.add_argument("token", nargs="?", help="Access token")

    subparsers.add_parser("funds", help="Show funds and margins")
    subparsers.add_parser("positions", help="Show open positions")
    subparsers.add_parser("holdings", help="Show demat holdings")
    subparsers.add_parser("orders", help="Show order book")

    quote_parser = subparsers.add_parser("quote", help="Get quote for symbol")
    quote_parser.add_argument("symbol", help="Trading symbol e.g. RELIANCE-EQ")
    quote_parser.add_argument("--exchange", default="NSE", help="Exchange (default: NSE)")

    buy_parser = subparsers.add_parser("buy", help="Place buy order")
    buy_parser.add_argument("symbol", help="Trading symbol")
    buy_parser.add_argument("qty", type=int, help="Quantity")
    buy_parser.add_argument("price", type=float, help="Limit price (0 for market)")
    buy_parser.add_argument("--product", default="CNC", help="Product type: CNC, MIS, NRML")
    buy_parser.add_argument("--order-type", default="LIMIT", help="LIMIT or MARKET")
    buy_parser.add_argument("--exchange", default="NSE", help="Exchange")

    sell_parser = subparsers.add_parser("sell", help="Place sell order")
    sell_parser.add_argument("symbol", help="Trading symbol")
    sell_parser.add_argument("qty", type=int, help="Quantity")
    sell_parser.add_argument("price", type=float, help="Limit price (0 for market)")
    sell_parser.add_argument("--product", default="CNC", help="Product type: CNC, MIS, NRML")
    sell_parser.add_argument("--order-type", default="LIMIT", help="LIMIT or MARKET")
    sell_parser.add_argument("--exchange", default="NSE", help="Exchange")

    cancel_parser = subparsers.add_parser("cancel", help="Cancel open order")
    cancel_parser.add_argument("order_id", help="Order ID to cancel")

    stream_parser = subparsers.add_parser("stream", help="Stream live market data")
    stream_parser.add_argument("tokens", help="Comma-separated instrument tokens, e.g. 3045,1594")

    serve_parser = subparsers.add_parser("serve", help="Launch FastAPI web dashboard")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host (default: 127.0.0.1)")

    args = parser.parse_args()

    if not args.command:
        interactive_menu()
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "login":
        cmd_login(args)
    elif args.command == "web-login":
        cmd_web_login(args)
    elif args.command == "exchange":
        cmd_exchange_token(args)
    elif args.command == "token":
        cmd_set_token(args)
    elif args.command == "funds":
        cmd_funds(args)
    elif args.command == "positions":
        cmd_positions(args)
    elif args.command == "holdings":
        cmd_holdings(args)
    elif args.command == "orders":
        cmd_orders(args)
    elif args.command == "quote":
        cmd_quote(args)
    elif args.command == "buy":
        cmd_place_order(args, transaction_type="BUY")
    elif args.command == "sell":
        cmd_place_order(args, transaction_type="SELL")
    elif args.command == "cancel":
        cmd_cancel(args)
    elif args.command == "stream":
        cmd_stream(args)
    elif args.command == "serve":
        cmd_serve(args)


if __name__ == "__main__":
    main()
