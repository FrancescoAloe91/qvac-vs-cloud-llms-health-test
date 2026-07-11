"""Wallet locale USDT (simulato) persistito su disco."""

import json
from datetime import datetime
from pathlib import Path

WALLET_PATH = Path(__file__).resolve().parent.parent / "data" / "wallet.json"

REWARD_DATA_SALE = 5.00


def load_wallet() -> dict:
    if WALLET_PATH.exists():
        return json.loads(WALLET_PATH.read_text())
    return {"balance": 0.0, "transactions": []}


def save_wallet(wallet: dict) -> None:
    WALLET_PATH.parent.mkdir(parents=True, exist_ok=True)
    WALLET_PATH.write_text(json.dumps(wallet, indent=2, ensure_ascii=False))


def add_reward(wallet: dict, amount: float, reason: str) -> dict:
    wallet["balance"] = round(wallet["balance"] + amount, 2)
    wallet["transactions"].append(
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "amount": amount,
            "reason": reason,
        }
    )
    save_wallet(wallet)
    return wallet


def reset_wallet() -> dict:
    """Azzera saldo e storico transazioni."""
    wallet = {"balance": 0.0, "transactions": []}
    save_wallet(wallet)
    return wallet
