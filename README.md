# Binance Futures Testnet Trading Bot

A clean, reusable Python application for placing **MARKET** and **LIMIT** orders on the [Binance Futures Testnet (USDT-M)](https://testnet.binancefuture.com/).

## Features

- Place **MARKET** and **LIMIT** orders (BUY / SELL)
- **Tkinter GUI** — dark-themed desktop interface with live connection status, order form, and scrollable order log
- Two CLI modes: **direct flags** and **interactive prompt wizard**
- Rich, colour-coded terminal output (powered by [Rich](https://github.com/Textualize/rich))
- HMAC-SHA256 request signing
- Rotating file-based logging (`logs/trading_bot.log`)
- Comprehensive input validation with clear error messages
- Structured, layered architecture (client → orders → CLI)

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py          # Package marker
│   ├── client.py            # Low-level Binance HTTP client (auth, signing)
│   ├── orders.py            # Order-building & submission logic
│   ├── validators.py        # Input validation & OrderParams dataclass
│   └── logging_config.py    # Dual file + console logging setup
├── cli.py                   # CLI entry point (argparse + Rich)
├── gui.py                   # Tkinter GUI entry point
├── .env.example             # Template for API credentials
├── .gitignore
├── requirements.txt
└── README.md
```

## Quick Start

### 1. Clone & install

```bash
cd binnace-trading-bot
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure credentials

```bash
copy .env.example .env      # Windows
# cp .env.example .env      # macOS / Linux
```

Edit `.env` and paste your **testnet** API key and secret.  
Generate them at <https://testnet.binancefuture.com/>.

### 3. Test connectivity

```bash
python cli.py ping
```

### 4. Launch the GUI (optional)

```bash
python gui.py
```

A dark-themed window opens with a live connection indicator, order form, confirmation dialog, and scrollable order log.

### 5. Place an order (CLI)

#### Direct mode

```bash
# Market buy 0.01 BTC
python cli.py order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

# Limit sell 0.5 ETH at 4000 USDT
python cli.py order --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.5 --price 4000
```

#### Interactive mode

```bash
python cli.py interactive
```

You'll be guided through each field with validation and a confirmation step before the order is submitted.

## CLI Reference

| Command       | Description                              |
| ------------- | ---------------------------------------- |
| `ping`        | Test connectivity to Binance Testnet     |
| `order`       | Place an order via command-line flags    |
| `interactive` | Launch the guided interactive prompt     |

### `order` flags

| Flag              | Required | Description                            |
| ----------------- | -------- | -------------------------------------- |
| `--symbol`, `-s`  | Yes      | Trading pair, e.g. `BTCUSDT`          |
| `--side`, `-S`    | Yes      | `BUY` or `SELL`                        |
| `--type`, `-t`    | Yes      | `MARKET` or `LIMIT`                    |
| `--quantity`, `-q`| Yes      | Order quantity                         |
| `--price`, `-p`   | No       | Limit price (required when type=LIMIT) |

## Logging

All API requests, responses, and errors are written to `logs/trading_bot.log` (rotating, max 5 MB × 3 backups). Console output shows INFO-level messages; the file captures DEBUG-level detail.

## Important Notes

- This bot targets the **testnet** only (`https://demo-fapi.binance.com`). Do **not** use real (mainnet) API keys.
- Always verify orders on the [Testnet UI](https://testnet.binancefuture.com/) after submission.