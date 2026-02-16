#!/usr/bin/env python3
"""Tkinter GUI for the Binance Futures Testnet Trading Bot.

Launch with:
    python gui.py
"""

from __future__ import annotations

import os
import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from dotenv import load_dotenv

from bot.client import BinanceAPIError, BinanceClient
from bot.logging_config import setup_logging
from bot.orders import place_order
from bot.validators import ValidationError, validate_order

# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

load_dotenv()
logger = setup_logging()

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------

BG = "#1e1e2e"
BG_SECONDARY = "#282840"
BG_CARD = "#313150"
FG = "#cdd6f4"
FG_DIM = "#6c7086"
ACCENT = "#89b4fa"
GREEN = "#a6e3a1"
RED = "#f38ba8"
YELLOW = "#f9e2af"
BORDER = "#45475a"
ENTRY_BG = "#3b3b58"


def _get_client() -> BinanceClient:
    """Build an authenticated BinanceClient from environment variables."""
    api_key = os.getenv("BINANCE_API_KEY") or os.getenv("BINANCE_TESTNET_API_KEY", "")
    api_secret = os.getenv("BINANCE_API_SECRET") or os.getenv("BINANCE_TESTNET_API_SECRET", "")
    if not api_key or not api_secret:
        raise ValueError(
            "API credentials not found.\n"
            "Set BINANCE_API_KEY and BINANCE_API_SECRET in your .env file."
        )
    return BinanceClient(api_key=api_key, api_secret=api_secret)


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  Main Application Window                                                 ║
# ╚═══════════════════════════════════════════════════════════════════════════╝


class TradingBotGUI:
    """Main GUI window for the trading bot."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Binance Futures Testnet — Trading Bot")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        # Centre the window
        win_w, win_h = 720, 780
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - win_w) // 2
        y = (screen_h - win_h) // 2
        self.root.geometry(f"{win_w}x{win_h}+{x}+{y}")

        self._client: BinanceClient | None = None
        self._connected = False

        self._build_styles()
        self._build_ui()

        # Try to connect on launch
        self.root.after(300, self._ping_async)

    # ------------------------------------------------------------------
    # ttk styles
    # ------------------------------------------------------------------

    def _build_styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(".", background=BG, foreground=FG, fieldbackground=ENTRY_BG)
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=BG_CARD)
        style.configure("TLabel", background=BG, foreground=FG, font=("Segoe UI", 10))
        style.configure("Card.TLabel", background=BG_CARD, foreground=FG, font=("Segoe UI", 10))
        style.configure("Header.TLabel", background=BG, foreground=ACCENT, font=("Segoe UI", 18, "bold"))
        style.configure("Sub.TLabel", background=BG, foreground=FG_DIM, font=("Segoe UI", 9))
        style.configure("Status.TLabel", background=BG_CARD, foreground=FG_DIM, font=("Segoe UI", 9))
        style.configure("SectionTitle.TLabel", background=BG, foreground=ACCENT, font=("Segoe UI", 11, "bold"))

        # Buttons
        style.configure(
            "Accent.TButton",
            background=ACCENT,
            foreground="#1e1e2e",
            font=("Segoe UI", 10, "bold"),
            padding=(16, 8),
        )
        style.map("Accent.TButton", background=[("active", "#74a0e3"), ("disabled", BORDER)])

        style.configure(
            "Buy.TButton",
            background=GREEN,
            foreground="#1e1e2e",
            font=("Segoe UI", 11, "bold"),
            padding=(20, 10),
        )
        style.map("Buy.TButton", background=[("active", "#8cd694"), ("disabled", BORDER)])

        style.configure(
            "Sell.TButton",
            background=RED,
            foreground="#1e1e2e",
            font=("Segoe UI", 11, "bold"),
            padding=(20, 10),
        )
        style.map("Sell.TButton", background=[("active", "#e07a96"), ("disabled", BORDER)])

        style.configure(
            "Ping.TButton",
            background=BG_CARD,
            foreground=ACCENT,
            font=("Segoe UI", 9),
            padding=(8, 4),
        )
        style.map("Ping.TButton", background=[("active", BG_SECONDARY)])

        # Combobox / Entry
        style.configure("TCombobox", fieldbackground=ENTRY_BG, foreground=FG, padding=6)
        style.map("TCombobox", fieldbackground=[("readonly", ENTRY_BG)])
        style.configure("TEntry", fieldbackground=ENTRY_BG, foreground=FG, padding=6)

        # Radio buttons
        style.configure("Side.TRadiobutton", background=BG_CARD, foreground=FG, font=("Segoe UI", 10))
        style.map("Side.TRadiobutton", background=[("active", BG_CARD)])

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # ── Header ──
        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill="x", padx=20, pady=(18, 0))
        ttk.Label(header_frame, text="Binance Futures Testnet", style="Header.TLabel").pack(side="left")

        # Connection indicator (right side of header)
        conn_frame = ttk.Frame(header_frame)
        conn_frame.pack(side="right")
        self._status_dot = tk.Canvas(conn_frame, width=12, height=12, bg=BG, highlightthickness=0)
        self._status_dot.pack(side="left", padx=(0, 6))
        self._draw_dot(FG_DIM)
        self._status_label = ttk.Label(conn_frame, text="Checking...", style="Sub.TLabel")
        self._status_label.pack(side="left")
        ttk.Button(conn_frame, text="Ping", style="Ping.TButton", command=self._ping_async).pack(
            side="left", padx=(10, 0)
        )

        ttk.Label(self.root, text="USDT-M  \u2022  Place Market & Limit Orders", style="Sub.TLabel").pack(
            anchor="w", padx=20, pady=(2, 12)
        )

        # ── Separator ──
        ttk.Separator(self.root).pack(fill="x", padx=20)

        # ── Order Form ──
        ttk.Label(self.root, text="New Order", style="SectionTitle.TLabel").pack(
            anchor="w", padx=20, pady=(14, 8)
        )

        form = ttk.Frame(self.root, style="Card.TFrame", padding=16)
        form.pack(fill="x", padx=20)

        # Row 0 — Symbol
        ttk.Label(form, text="Symbol", style="Card.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        self._symbol_var = tk.StringVar(value="BTCUSDT")
        symbol_entry = ttk.Entry(form, textvariable=self._symbol_var, width=20)
        symbol_entry.grid(row=0, column=1, sticky="w", padx=(12, 0), pady=(0, 8))

        # Row 1 — Side (radio)
        ttk.Label(form, text="Side", style="Card.TLabel").grid(row=1, column=0, sticky="w", pady=(0, 8))
        side_frame = ttk.Frame(form, style="Card.TFrame")
        side_frame.grid(row=1, column=1, sticky="w", padx=(12, 0), pady=(0, 8))
        self._side_var = tk.StringVar(value="BUY")
        ttk.Radiobutton(side_frame, text="BUY", variable=self._side_var, value="BUY", style="Side.TRadiobutton").pack(
            side="left", padx=(0, 16)
        )
        ttk.Radiobutton(
            side_frame, text="SELL", variable=self._side_var, value="SELL", style="Side.TRadiobutton"
        ).pack(side="left")

        # Row 2 — Order type
        ttk.Label(form, text="Type", style="Card.TLabel").grid(row=2, column=0, sticky="w", pady=(0, 8))
        self._type_var = tk.StringVar(value="MARKET")
        type_combo = ttk.Combobox(
            form,
            textvariable=self._type_var,
            values=["MARKET", "LIMIT"],
            state="readonly",
            width=17,
        )
        type_combo.grid(row=2, column=1, sticky="w", padx=(12, 0), pady=(0, 8))
        type_combo.bind("<<ComboboxSelected>>", self._on_type_changed)

        # Row 3 — Quantity
        ttk.Label(form, text="Quantity", style="Card.TLabel").grid(row=3, column=0, sticky="w", pady=(0, 8))
        self._qty_var = tk.StringVar()
        ttk.Entry(form, textvariable=self._qty_var, width=20).grid(
            row=3, column=1, sticky="w", padx=(12, 0), pady=(0, 8)
        )

        # Row 4 — Price (hidden for MARKET)
        self._price_label = ttk.Label(form, text="Price", style="Card.TLabel")
        self._price_label.grid(row=4, column=0, sticky="w", pady=(0, 4))
        self._price_var = tk.StringVar()
        self._price_entry = ttk.Entry(form, textvariable=self._price_var, width=20)
        self._price_entry.grid(row=4, column=1, sticky="w", padx=(12, 0), pady=(0, 4))
        self._toggle_price_field()

        # Configure grid weights so form stretches
        form.columnconfigure(1, weight=1)

        # ── Submit buttons ──
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill="x", padx=20, pady=(14, 0))

        self._submit_btn = ttk.Button(btn_frame, text="PLACE ORDER", style="Buy.TButton", command=self._submit_order)
        self._submit_btn.pack(fill="x")
        # Dynamically colour the button via side var
        self._side_var.trace_add("write", self._on_side_changed)

        # ── Separator ──
        ttk.Separator(self.root).pack(fill="x", padx=20, pady=(16, 0))

        # ── Response / Log area ──
        ttk.Label(self.root, text="Order Log", style="SectionTitle.TLabel").pack(
            anchor="w", padx=20, pady=(12, 6)
        )

        log_frame = ttk.Frame(self.root, style="Card.TFrame", padding=2)
        log_frame.pack(fill="both", expand=True, padx=20, pady=(0, 18))

        self._log_text = tk.Text(
            log_frame,
            bg=BG_CARD,
            fg=FG,
            insertbackground=FG,
            font=("Consolas", 9),
            relief="flat",
            wrap="word",
            state="disabled",
            height=12,
            padx=10,
            pady=8,
        )
        scrollbar = ttk.Scrollbar(log_frame, command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._log_text.pack(side="left", fill="both", expand=True)

        # Tag colours for the log
        self._log_text.tag_configure("timestamp", foreground=FG_DIM)
        self._log_text.tag_configure("info", foreground=ACCENT)
        self._log_text.tag_configure("success", foreground=GREEN)
        self._log_text.tag_configure("error", foreground=RED)
        self._log_text.tag_configure("warn", foreground=YELLOW)
        self._log_text.tag_configure("label", foreground=FG_DIM)
        self._log_text.tag_configure("value", foreground=FG)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _draw_dot(self, colour: str) -> None:
        self._status_dot.delete("all")
        self._status_dot.create_oval(2, 2, 10, 10, fill=colour, outline=colour)

    def _log(self, message: str, tag: str = "info") -> None:
        """Append a line to the order-log text widget."""
        self._log_text.configure(state="normal")
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_text.insert("end", f"[{ts}] ", "timestamp")
        self._log_text.insert("end", f"{message}\n", tag)
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    def _log_kv(self, label: str, value: str, tag: str = "value") -> None:
        """Append a key-value pair to the log."""
        self._log_text.configure(state="normal")
        self._log_text.insert("end", f"  {label}: ", "label")
        self._log_text.insert("end", f"{value}\n", tag)
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    def _toggle_price_field(self) -> None:
        is_limit = self._type_var.get() == "LIMIT"
        state = "normal" if is_limit else "disabled"
        self._price_entry.configure(state=state)
        if not is_limit:
            self._price_var.set("")

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self._submit_btn.configure(state=state)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_type_changed(self, _event=None) -> None:
        self._toggle_price_field()

    def _on_side_changed(self, *_args) -> None:
        side = self._side_var.get()
        style = "Buy.TButton" if side == "BUY" else "Sell.TButton"
        label = f"PLACE {side} ORDER"
        self._submit_btn.configure(style=style, text=label)

    # ------------------------------------------------------------------
    # Ping
    # ------------------------------------------------------------------

    def _ping_async(self) -> None:
        self._status_label.configure(text="Connecting...")
        self._draw_dot(YELLOW)
        threading.Thread(target=self._ping_worker, daemon=True).start()

    def _ping_worker(self) -> None:
        try:
            client = _get_client()
            client.ping()
            self._client = client
            self._connected = True
            self.root.after(0, self._ping_ok)
        except Exception as exc:
            self._connected = False
            self.root.after(0, self._ping_fail, str(exc))

    def _ping_ok(self) -> None:
        self._draw_dot(GREEN)
        self._status_label.configure(text="Connected")
        self._log("Connected to Binance Futures Testnet", "success")

    def _ping_fail(self, err: str) -> None:
        self._draw_dot(RED)
        self._status_label.configure(text="Disconnected")
        self._log(f"Connection failed: {err}", "error")

    # ------------------------------------------------------------------
    # Order submission
    # ------------------------------------------------------------------

    def _submit_order(self) -> None:
        symbol = self._symbol_var.get().strip()
        side = self._side_var.get()
        order_type = self._type_var.get()
        quantity = self._qty_var.get().strip()
        price = self._price_var.get().strip() or None

        # --- Validate ---
        try:
            params = validate_order(symbol, side, order_type, quantity, price)
        except ValidationError as exc:
            self._log(f"Validation error — {exc}", "error")
            messagebox.showwarning("Validation Error", str(exc))
            return

        # --- Confirm ---
        summary = (
            f"Symbol:   {params.symbol}\n"
            f"Side:       {params.side}\n"
            f"Type:       {params.order_type}\n"
            f"Quantity: {params.quantity}"
        )
        if params.price is not None:
            summary += f"\nPrice:      {params.price}"
        if not messagebox.askokcancel("Confirm Order", f"Place this order?\n\n{summary}"):
            self._log("Order cancelled by user.", "warn")
            return

        # --- Submit in background ---
        self._set_busy(True)
        self._log(
            f"Submitting {params.side} {params.order_type} {params.symbol} "
            f"qty={params.quantity}"
            + (f" price={params.price}" if params.price else ""),
            "info",
        )
        threading.Thread(target=self._order_worker, args=(params,), daemon=True).start()

    def _order_worker(self, params) -> None:
        try:
            client = self._client or _get_client()
            response = place_order(client, params)
            self.root.after(0, self._order_ok, response)
        except BinanceAPIError as exc:
            self.root.after(0, self._order_fail, f"API Error: {exc}")
        except Exception as exc:
            self.root.after(0, self._order_fail, f"Error: {exc}")

    def _order_ok(self, resp: dict) -> None:
        self._set_busy(False)
        self._log("Order placed successfully!", "success")

        fields = [
            ("Order ID", "orderId"),
            ("Status", "status"),
            ("Symbol", "symbol"),
            ("Side", "side"),
            ("Type", "type"),
            ("Orig Qty", "origQty"),
            ("Executed Qty", "executedQty"),
            ("Avg Price", "avgPrice"),
            ("Time In Force", "timeInForce"),
        ]
        for label, key in fields:
            val = resp.get(key)
            if val is not None:
                tag = "value"
                if key == "status":
                    tag = "success" if val in ("NEW", "FILLED", "PARTIALLY_FILLED") else "warn"
                self._log_kv(label, str(val), tag)

        self._log("—" * 50, "info")

    def _order_fail(self, err: str) -> None:
        self._set_busy(False)
        self._log(err, "error")
        messagebox.showerror("Order Failed", err)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    root = tk.Tk()
    TradingBotGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
