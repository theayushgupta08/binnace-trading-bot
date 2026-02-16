#!/usr/bin/env python3
"""CLI entry point for the Binance Futures Testnet Trading Bot.

Supports two modes:

1. **Direct** — pass all arguments on the command line:
       python cli.py order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

2. **Interactive** — launch a guided prompt wizard:
       python cli.py interactive
"""

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from bot.client import BinanceAPIError, BinanceClient
from bot.logging_config import setup_logging
from bot.orders import place_order
from bot.validators import ValidationError, validate_order

# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

load_dotenv()
logger = setup_logging()
console = Console()

BANNER = r"""
 ____  _                              ____        _
| __ )(_)_ __   __ _ _ __   ___ ___ | __ )  ___ | |_
|  _ \| | '_ \ / _` | '_ \ / __/ _ \|  _ \ / _ \| __|
| |_) | | | | | (_| | | | | (_|  __/| |_) | (_) | |_
|____/|_|_| |_|\__,_|_| |_|\___\___||____/ \___/ \__|
        Futures Testnet Trading Bot  v1.0.0
"""


def _get_client() -> BinanceClient:
    """Build an authenticated ``BinanceClient`` from environment variables."""
    api_key = os.getenv("BINANCE_API_KEY") or os.getenv("BINANCE_TESTNET_API_KEY", "")
    api_secret = os.getenv("BINANCE_API_SECRET") or os.getenv("BINANCE_TESTNET_API_SECRET", "")
    if not api_key or not api_secret:
        console.print(
            "[bold red]Error:[/] API credentials not found. Set BINANCE_API_KEY and "
            "BINANCE_API_SECRET (or BINANCE_TESTNET_API_KEY / BINANCE_TESTNET_API_SECRET).\n"
            "Copy .env.example to .env and fill in your testnet credentials."
        )
        sys.exit(1)
    return BinanceClient(api_key=api_key, api_secret=api_secret)


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def _print_order_summary(params) -> None:
    """Pretty-print the order request before sending."""
    table = Table(title="Order Request Summary", show_header=False, border_style="cyan")
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("Symbol", params.symbol)
    table.add_row("Side", f"[green]{params.side}[/]" if params.side == "BUY" else f"[red]{params.side}[/]")
    table.add_row("Type", params.order_type)
    table.add_row("Quantity", str(params.quantity))
    if params.price is not None:
        table.add_row("Price", str(params.price))
    console.print()
    console.print(table)


def _print_order_response(resp: dict) -> None:
    """Pretty-print the order response from Binance."""
    table = Table(title="Order Response", show_header=False, border_style="green")
    table.add_column("Field", style="bold")
    table.add_column("Value")

    fields = [
        ("Order ID", "orderId"),
        ("Client Order ID", "clientOrderId"),
        ("Symbol", "symbol"),
        ("Side", "side"),
        ("Type", "type"),
        ("Status", "status"),
        ("Orig Qty", "origQty"),
        ("Executed Qty", "executedQty"),
        ("Avg Price", "avgPrice"),
        ("Cum Quote", "cumQuote"),
        ("Time In Force", "timeInForce"),
        ("Update Time", "updateTime"),
    ]
    for label, key in fields:
        value = resp.get(key)
        if value is not None:
            # Colour the status
            display = str(value)
            if key == "status":
                colour = "green" if value in ("NEW", "FILLED", "PARTIALLY_FILLED") else "yellow"
                display = f"[{colour}]{value}[/{colour}]"
            table.add_row(label, display)

    console.print()
    console.print(table)


# ---------------------------------------------------------------------------
# Core order flow
# ---------------------------------------------------------------------------


def _execute_order(symbol: str, side: str, order_type: str, quantity, price=None) -> None:
    """Validate, confirm, submit, and display an order."""
    try:
        params = validate_order(symbol, side, order_type, quantity, price)
    except ValidationError as exc:
        console.print(f"[bold red]Validation error:[/] {exc}")
        logger.error("Validation failed: %s", exc)
        sys.exit(1)

    _print_order_summary(params)

    # Ask for confirmation in interactive/direct mode
    if not Confirm.ask("\n[bold]Submit this order?[/]", default=False):
        console.print("[yellow]Order cancelled by user.[/]")
        return

    client = _get_client()

    # Connectivity check
    console.print("\n[dim]Testing API connectivity...[/]", end=" ")
    try:
        client.ping()
        console.print("[green]OK[/]")
    except Exception as exc:
        console.print(f"[red]FAILED[/]")
        console.print(f"[bold red]Cannot reach Binance Testnet:[/] {exc}")
        logger.error("Ping failed: %s", exc)
        sys.exit(1)

    # Place the order
    try:
        response = place_order(client, params)
    except BinanceAPIError as exc:
        console.print(f"\n[bold red]API Error:[/] {exc}")
        logger.error("API error placing order: %s", exc)
        sys.exit(1)
    except Exception as exc:
        console.print(f"\n[bold red]Unexpected error:[/] {exc}")
        logger.exception("Unexpected error placing order")
        sys.exit(1)

    _print_order_response(response)
    console.print(Panel("[bold green]Order submitted successfully![/]", border_style="green"))


# ---------------------------------------------------------------------------
# CLI sub-commands
# ---------------------------------------------------------------------------


def cmd_order(args: argparse.Namespace) -> None:
    """Handle the ``order`` sub-command."""
    _execute_order(
        symbol=args.symbol,
        side=args.side,
        order_type=args.type,
        quantity=args.quantity,
        price=args.price,
    )


def cmd_interactive(_args: argparse.Namespace) -> None:
    """Handle the ``interactive`` sub-command — guided prompt wizard."""
    console.print(Panel(BANNER, border_style="bright_blue", expand=False))

    symbol = Prompt.ask("[bold]Symbol[/]", default="BTCUSDT")
    side = Prompt.ask("[bold]Side[/]", choices=["BUY", "SELL"], default="BUY")
    order_type = Prompt.ask("[bold]Order type[/]", choices=["MARKET", "LIMIT"], default="MARKET")
    quantity = Prompt.ask("[bold]Quantity[/]")

    price = None
    if order_type == "LIMIT":
        price = Prompt.ask("[bold]Price[/]")

    _execute_order(symbol=symbol, side=side, order_type=order_type, quantity=quantity, price=price)


def cmd_ping(_args: argparse.Namespace) -> None:
    """Handle the ``ping`` sub-command — test API connectivity."""
    client = _get_client()
    try:
        client.ping()
        console.print("[bold green]Binance Futures Testnet is reachable.[/]")
    except Exception as exc:
        console.print(f"[bold red]Ping failed:[/] {exc}")
        logger.error("Ping failed: %s", exc)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Construct the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="trading-bot",
        description="Binance Futures Testnet Trading Bot — place MARKET and LIMIT orders.",
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # --- order ---
    p_order = sub.add_parser("order", help="Place an order directly via CLI flags")
    p_order.add_argument("--symbol", "-s", required=True, help="Trading pair (e.g. BTCUSDT)")
    p_order.add_argument("--side", "-S", required=True, choices=["BUY", "SELL"], help="Order side")
    p_order.add_argument("--type", "-t", required=True, choices=["MARKET", "LIMIT"], help="Order type")
    p_order.add_argument("--quantity", "-q", required=True, help="Order quantity")
    p_order.add_argument("--price", "-p", default=None, help="Limit price (required for LIMIT orders)")
    p_order.set_defaults(func=cmd_order)

    # --- interactive ---
    p_inter = sub.add_parser("interactive", help="Launch guided interactive prompt")
    p_inter.set_defaults(func=cmd_interactive)

    # --- ping ---
    p_ping = sub.add_parser("ping", help="Test API connectivity")
    p_ping.set_defaults(func=cmd_ping)

    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
