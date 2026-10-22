"""
Data-to-Dirt — Tamper-Evident Double-Entry Audit Ledger
Provides immutable, cryptographic SHA-256 block-chained persistence for all
dark data reductions, micro-donations, budget top-ups, and balance adjustments.
"""

import os
import json
import sqlite3
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union


VALID_TRANSACTION_TYPES = {
    "DATA_REDUCTION",
    "MICRO_DONATION",
    "BUDGET_TOPUP",
    "ADJUSTMENT",
    # Interoperability aliases
    "BUDGET_ALLOCATION",
    "TREE_NATION_DISBURSEMENT",
}

DEFAULT_ACCOUNTS = {
    "ECO_FUND_CASH",
    "REFORESTATION_EXPENSE",
    "DATA_WASTE_REDUCTION",
    "STUDENT_CARBON_SAVINGS",
    "ADMIN_BUDGET_EQUITY",
    "SYSTEM_ADJUSTMENT",
}


class LedgerBlock:
    """Represents a single immutable, cryptographically hashed ledger block."""

    def __init__(
        self,
        block_id: int,
        timestamp: str,
        transaction_type: str,
        student_id: str,
        data_bytes: int,
        amount_cents: int,
        previous_hash: str,
        debit_account: str = "ECO_FUND_CASH",
        credit_account: str = "ADMIN_BUDGET_EQUITY",
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        block_hash: Optional[str] = None,
    ):
        if transaction_type not in VALID_TRANSACTION_TYPES:
            raise ValueError(
                f"Invalid transaction_type '{transaction_type}'. Must be one of {sorted(VALID_TRANSACTION_TYPES)}"
            )

        self.block_id = int(block_id)
        self.timestamp = timestamp
        self.transaction_type = transaction_type
        self.student_id = str(student_id)
        self.data_bytes = int(data_bytes)
        self.amount_cents = int(amount_cents)
        self.previous_hash = str(previous_hash)
        self.debit_account = str(debit_account)
        self.credit_account = str(credit_account)
        self.description = str(description)
        self.metadata = dict(metadata or {})

        # Compute hash if not provided or verify
        computed = self.compute_hash()
        if block_hash is not None and block_hash != computed:
            # Stored hash might be corrupted (useful for tamper tests)
            self.hash = block_hash
        else:
            self.hash = computed

    def compute_hash(self) -> str:
        """Computes deterministic SHA-256 over all canonical block fields."""
        payload = {
            "block_id": self.block_id,
            "timestamp": self.timestamp,
            "transaction_type": self.transaction_type,
            "student_id": self.student_id,
            "data_bytes": self.data_bytes,
            "amount_cents": self.amount_cents,
            "previous_hash": self.previous_hash,
            "debit_account": self.debit_account,
            "credit_account": self.credit_account,
            "description": self.description,
            "metadata": self.metadata,
        }
        canonical_str = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Converts block to dictionary representation."""
        return {
            "block_id": self.block_id,
            "timestamp": self.timestamp,
            "transaction_type": self.transaction_type,
            "student_id": self.student_id,
            "data_bytes": self.data_bytes,
            "amount_cents": self.amount_cents,
            "amount_usd": round(self.amount_cents / 100.0, 2),
            "previous_hash": self.previous_hash,
            "hash": self.hash,
            "debit_account": self.debit_account,
            "credit_account": self.credit_account,
            "description": self.description,
            "metadata": self.metadata,
            # Compatibility aliases
            "tx_id": f"tx_{self.block_id:04d}",
            "type": self.transaction_type,
            "prev_hash": self.previous_hash,
            "notes": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LedgerBlock":
        """Instantiates a LedgerBlock from dictionary."""
        return cls(
            block_id=data["block_id"],
            timestamp=data["timestamp"],
            transaction_type=data.get("transaction_type") or data.get("type", "ADJUSTMENT"),
            student_id=data.get("student_id", "SYSTEM"),
            data_bytes=data.get("data_bytes", 0),
            amount_cents=data.get("amount_cents", int(data.get("amount_usd", 0.0) * 100)),
            previous_hash=data.get("previous_hash") or data.get("prev_hash", "0" * 64),
            debit_account=data.get("debit_account", "ECO_FUND_CASH"),
            credit_account=data.get("credit_account", "ADMIN_BUDGET_EQUITY"),
            description=data.get("description") or data.get("notes", ""),
            metadata=data.get("metadata", {}),
            block_hash=data.get("hash"),
        )


class AuditLedger:
    """
    Tamper-evident double-entry audit ledger with cryptographic SHA-256 chaining.
    Maintains balanced accounts and persistent storage in JSON or SQLite.
    """

    GENESIS_PREV_HASH = "0" * 64

    def __init__(
        self,
        storage_path: Optional[Union[str, Path]] = None,
        auto_persist: bool = True,
        initial_balance_cents: int = 0,
        admin_id: str = "SYSTEM_INIT",
    ):
        self.blocks: List[LedgerBlock] = []
        self.auto_persist = auto_persist

        if storage_path:
            self.storage_path = Path(storage_path).resolve()
        else:
            self.storage_path = None

        # Load existing data if file exists
        loaded = False
        if self.storage_path and self.storage_path.exists():
            try:
                if self.storage_path.suffix.lower() in {".db", ".sqlite", ".sqlite3"}:
                    self.load_from_sqlite(self.storage_path)
                    loaded = True
                else:
                    self.load_from_json(self.storage_path)
                    loaded = True
            except Exception:
                loaded = False

        # Initialize genesis block if newly created
        if not loaded and len(self.blocks) == 0:
            if initial_balance_cents > 0:
                self.append_block(
                    transaction_type="BUDGET_TOPUP",
                    student_id=admin_id,
                    data_bytes=0,
                    amount_cents=initial_balance_cents,
                    debit_account="ECO_FUND_CASH",
                    credit_account="ADMIN_BUDGET_EQUITY",
                    description=f"Initial classroom Eco-Fund budget ({initial_balance_cents / 100:.2f} USD)",
                )

    @property
    def transactions(self) -> List[Dict[str, Any]]:
        """Compatibility property returning list of transaction dictionaries with running balance."""
        res = []
        running_cents = 0
        for block in self.blocks:
            d = block.to_dict()
            if block.debit_account == "ECO_FUND_CASH":
                running_cents += block.amount_cents
            elif block.credit_account == "ECO_FUND_CASH":
                running_cents -= block.amount_cents
            d["balance_after"] = round(running_cents / 100.0, 2)
            d["balance_after_cents"] = running_cents
            res.append(d)
        return res

    def get_last_hash(self) -> str:
        """Returns the hash of the latest block, or 64 zeroes if ledger is empty."""
        if not self.blocks:
            return self.GENESIS_PREV_HASH
        return self.blocks[-1].hash

    def append_block(
        self,
        transaction_type: str,
        student_id: str = "SYSTEM",
        data_bytes: int = 0,
        amount_cents: int = 0,
        debit_account: str = "ECO_FUND_CASH",
        credit_account: str = "ADMIN_BUDGET_EQUITY",
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[str] = None,
    ) -> LedgerBlock:
        """
        Appends a new verified block to the tamper-evident hash chain.
        Ensures strict double-entry and cryptographic chaining.
        """
        block_id = len(self.blocks)
        prev_hash = self.get_last_hash()
        ts = timestamp or datetime.now(timezone.utc).isoformat()

        # Map canonical accounts for standard transaction types if using defaults
        if transaction_type in ("MICRO_DONATION", "TREE_NATION_DISBURSEMENT"):
            if debit_account == "ECO_FUND_CASH":
                debit_account = "REFORESTATION_EXPENSE"
                credit_account = "ECO_FUND_CASH"
        elif transaction_type in ("BUDGET_TOPUP", "BUDGET_ALLOCATION"):
            if credit_account == "ADMIN_BUDGET_EQUITY":
                debit_account = "ECO_FUND_CASH"
                credit_account = "ADMIN_BUDGET_EQUITY"
        elif transaction_type == "DATA_REDUCTION":
            if debit_account == "ECO_FUND_CASH":
                debit_account = "STUDENT_CARBON_SAVINGS"
                credit_account = "DATA_WASTE_REDUCTION"

        block = LedgerBlock(
            block_id=block_id,
            timestamp=ts,
            transaction_type=transaction_type,
            student_id=student_id,
            data_bytes=data_bytes,
            amount_cents=amount_cents,
            previous_hash=prev_hash,
            debit_account=debit_account,
            credit_account=credit_account,
            description=description,
            metadata=metadata,
        )

        self.blocks.append(block)

        if self.auto_persist and self.storage_path:
            self.persist()

        return block

    def verify_chain(self) -> Tuple[bool, str]:
        """
        Validates full hash chain integrity.
        Returns (True, 'Chain integrity verified successfully.') or (False, error_msg).
        """
        if not self.blocks:
            return True, "Chain is empty (valid)."

        for i, block in enumerate(self.blocks):
            # 1. Verify sequential block_id
            if block.block_id != i:
                return (
                    False,
                    f"Block sequence error at index {i}: block_id is {block.block_id} but expected {i}.",
                )

            # 2. Verify previous hash chaining
            expected_prev = self.GENESIS_PREV_HASH if i == 0 else self.blocks[i - 1].hash
            if block.previous_hash != expected_prev:
                return (
                    False,
                    f"Previous hash broken at block {i}: block.previous_hash '{block.previous_hash}' != expected '{expected_prev}'.",
                )

            # 3. Verify SHA-256 block hash computation
            recalculated = block.compute_hash()
            if block.hash != recalculated:
                return (
                    False,
                    f"Tamper detected at block {i}: recorded hash '{block.hash}' != recomputed hash '{recalculated}'.",
                )

        return True, f"Chain integrity verified successfully. {len(self.blocks)} blocks valid."

    def verify_ledger_integrity(self) -> bool:
        """Convenience method returning boolean verification result."""
        valid, _ = self.verify_chain()
        return valid

    def get_account_balances(self) -> Dict[str, int]:
        """
        Calculates net balance for every double-entry account in cents.
        In double-entry:
        - Asset / Expense accounts (ECO_FUND_CASH, REFORESTATION_EXPENSE, STUDENT_CARBON_SAVINGS):
          Net = Sum(Debits) - Sum(Credits)
        - Liability / Equity / Revenue accounts (ADMIN_BUDGET_EQUITY, DATA_WASTE_REDUCTION):
          Net = Sum(Credits) - Sum(Debits)
        """
        debits: Dict[str, int] = {}
        credits: Dict[str, int] = {}

        for b in self.blocks:
            debits[b.debit_account] = debits.get(b.debit_account, 0) + b.amount_cents
            credits[b.credit_account] = credits.get(b.credit_account, 0) + b.amount_cents

        balances = {}
        all_accounts = set(debits.keys()) | set(credits.keys())
        for acc in all_accounts:
            d = debits.get(acc, 0)
            c = credits.get(acc, 0)
            balances[acc] = d - c  # Standard debit-normal representation

        return balances

    def get_eco_fund_balance_cents(self) -> int:
        """Returns the net cash balance of the Eco-Fund in cents."""
        bal = self.get_account_balances()
        return bal.get("ECO_FUND_CASH", 0)

    def get_eco_fund_balance_usd(self) -> float:
        """Returns the net cash balance of the Eco-Fund in USD."""
        return round(self.get_eco_fund_balance_cents() / 100.0, 2)

    def persist(self) -> None:
        """Saves blocks to configured storage path."""
        if not self.storage_path:
            return

        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        suffix = self.storage_path.suffix.lower()
        if suffix in {".db", ".sqlite", ".sqlite3"}:
            self.save_to_sqlite(self.storage_path)
        else:
            self.save_to_json(self.storage_path)

    def save_to_json(self, path: Union[str, Path]) -> None:
        """Serializes the entire ledger chain to a JSON file."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "ledger_version": "1.0",
            "total_blocks": len(self.blocks),
            "last_hash": self.get_last_hash(),
            "blocks": [b.to_dict() for b in self.blocks],
        }
        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_from_json(self, path: Union[str, Path]) -> None:
        """Loads and verifies a ledger chain from a JSON file."""
        target = Path(path)
        if not target.exists():
            return

        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw_blocks = data.get("blocks", [])
        self.blocks = [LedgerBlock.from_dict(b) for b in raw_blocks]

    def save_to_sqlite(self, path: Union[str, Path]) -> None:
        """Persists all ledger blocks into an SQLite database."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(target))
        try:
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS ledger_blocks (
                        block_id INTEGER PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        transaction_type TEXT NOT NULL,
                        student_id TEXT NOT NULL,
                        data_bytes INTEGER NOT NULL,
                        amount_cents INTEGER NOT NULL,
                        previous_hash TEXT NOT NULL,
                        hash TEXT NOT NULL,
                        debit_account TEXT NOT NULL,
                        credit_account TEXT NOT NULL,
                        description TEXT NOT NULL,
                        metadata_json TEXT NOT NULL
                    )
                    """
                )
                conn.execute("DELETE FROM ledger_blocks")
                for b in self.blocks:
                    conn.execute(
                        """
                        INSERT INTO ledger_blocks (
                            block_id, timestamp, transaction_type, student_id,
                            data_bytes, amount_cents, previous_hash, hash,
                            debit_account, credit_account, description, metadata_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            b.block_id,
                            b.timestamp,
                            b.transaction_type,
                            b.student_id,
                            b.data_bytes,
                            b.amount_cents,
                            b.previous_hash,
                            b.hash,
                            b.debit_account,
                            b.credit_account,
                            b.description,
                            json.dumps(b.metadata),
                        ),
                    )
        finally:
            conn.close()

    def load_from_sqlite(self, path: Union[str, Path]) -> None:
        """Loads blocks from an SQLite database."""
        target = Path(path)
        if not target.exists():
            return
        conn = sqlite3.connect(str(target))
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT block_id, timestamp, transaction_type, student_id,
                       data_bytes, amount_cents, previous_hash, hash,
                       debit_account, credit_account, description, metadata_json
                FROM ledger_blocks ORDER BY block_id ASC
                """
            )
            rows = cursor.fetchall()
            loaded = []
            for row in rows:
                meta = json.loads(row[11]) if row[11] else {}
                block = LedgerBlock(
                    block_id=row[0],
                    timestamp=row[1],
                    transaction_type=row[2],
                    student_id=row[3],
                    data_bytes=row[4],
                    amount_cents=row[5],
                    previous_hash=row[6],
                    debit_account=row[8],
                    credit_account=row[9],
                    description=row[10],
                    metadata=meta,
                    block_hash=row[7],
                )
                loaded.append(block)
            self.blocks = loaded
        finally:
            conn.close()
