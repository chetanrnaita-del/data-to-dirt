"""
Data-to-Dirt — Eco-Fund Management & Cumulative Waste Accumulator
Coordinates verified dark data waste accumulation toward a configurable 1.0 GB threshold,
triggers automated micro-donations via Tree-Nation, records cryptographic audit ledger blocks,
and enforces budget safety caps with real-time alerts.
"""

import math
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path

from src.services.ledger import AuditLedger, LedgerBlock
from src.services.tree_nation import TreeNationClient


DEFAULT_THRESHOLD_BYTES = 1024 * 1024 * 1024  # 1.0 GB = 1,073,741,824 bytes
DEFAULT_COST_PER_TREE_CENTS = 150              # $1.50 USD per tree planted


class EcoFundManager:
    """
    Manages the classroom / organization Eco-Fund.
    Tracks approved dark data deletions, triggers reforestation micro-donations
    when crossing thresholds, and enforces double-entry ledger integrity.
    """

    def __init__(
        self,
        initial_budget_usd: Optional[float] = None,
        initial_balance_cents: Optional[int] = None,
        threshold_bytes: int = DEFAULT_THRESHOLD_BYTES,
        cost_per_tree_cents: Optional[int] = None,
        cost_per_tree_usd: Optional[float] = None,
        ledger: Optional[AuditLedger] = None,
        tree_client: Optional[TreeNationClient] = None,
        storage_path: Optional[Union[str, Path]] = None,
        admin_id: str = "TEACHER_ADMIN",
    ):
        self.threshold_bytes = int(threshold_bytes)

        # Initialize cost per tree
        if cost_per_tree_cents is not None:
            self.cost_per_tree_cents = int(cost_per_tree_cents)
        elif cost_per_tree_usd is not None:
            self.cost_per_tree_cents = int(round(cost_per_tree_usd * 100))
        else:
            self.cost_per_tree_cents = DEFAULT_COST_PER_TREE_CENTS

        # Initialize ledger
        if ledger is not None:
            self.ledger = ledger
        else:
            init_cents = 0
            if initial_balance_cents is not None:
                init_cents = int(initial_balance_cents)
            elif initial_budget_usd is not None:
                init_cents = int(round(initial_budget_usd * 100))
            else:
                init_cents = 10000  # Default $100.00 initial budget

            self.ledger = AuditLedger(
                storage_path=storage_path,
                initial_balance_cents=init_cents,
                admin_id=admin_id,
            )

        # Initialize Tree-Nation client
        self.tree_client = tree_client if tree_client is not None else TreeNationClient()

        # State counters
        self.cumulative_waste_bytes: int = 0
        self.donated_bytes: int = 0
        self.lifetime_trees: int = 0
        self.pending_trees_count: int = 0
        self.latest_alert: Optional[Dict[str, Any]] = None
        self.donations_history: List[Dict[str, Any]] = []

    @property
    def budget_usd(self) -> float:
        """Returns the current Eco-Fund balance in USD."""
        return self.ledger.get_eco_fund_balance_usd()

    @budget_usd.setter
    def budget_usd(self, new_usd: float) -> None:
        """Updates balance by logging an adjustment block if different."""
        current_cents = self.ledger.get_eco_fund_balance_cents()
        target_cents = int(round(new_usd * 100))
        diff = target_cents - current_cents
        if diff != 0:
            if diff > 0:
                self.ledger.append_block(
                    transaction_type="BUDGET_TOPUP",
                    student_id="ADMIN",
                    data_bytes=0,
                    amount_cents=diff,
                    description=f"Budget adjustment (+{diff/100:.2f} USD)",
                )
            else:
                self.ledger.append_block(
                    transaction_type="ADJUSTMENT",
                    student_id="ADMIN",
                    data_bytes=0,
                    amount_cents=abs(diff),
                    debit_account="ADMIN_BUDGET_EQUITY",
                    credit_account="ECO_FUND_CASH",
                    description=f"Budget adjustment (-{abs(diff)/100:.2f} USD)",
                )

    @property
    def balance_usd(self) -> float:
        """Alias for budget_usd."""
        return self.budget_usd

    @property
    def cost_per_tree_usd(self) -> float:
        """Returns the cost per tree in USD."""
        return round(self.cost_per_tree_cents / 100.0, 2)

    @property
    def surplus_bytes(self) -> int:
        """Returns the accumulated bytes beyond already donated trees."""
        return max(0, self.cumulative_waste_bytes - self.donated_bytes)

    @property
    def transactions(self) -> List[Dict[str, Any]]:
        """Compatibility property for ledger transactions."""
        return self.ledger.transactions

    def verify_ledger_integrity(self) -> bool:
        """Verifies the underlying cryptographic SHA-256 hash chain."""
        return self.ledger.verify_ledger_integrity()

    def verify_chain(self) -> Tuple[bool, str]:
        """Returns detailed verification tuple from the ledger."""
        return self.ledger.verify_chain()

    def set_budget(self, new_balance_usd: float, admin_id: str = "ADMIN", reason: str = "Admin budget update") -> Dict[str, Any]:
        """Explicitly sets the available budget in USD."""
        current_cents = self.ledger.get_eco_fund_balance_cents()
        target_cents = int(round(new_balance_usd * 100))
        diff = target_cents - current_cents

        if diff > 0:
            self.ledger.append_block(
                transaction_type="BUDGET_TOPUP",
                student_id=admin_id,
                data_bytes=0,
                amount_cents=diff,
                description=f"{reason} (+{diff/100:.2f} USD)",
            )
        elif diff < 0:
            self.ledger.append_block(
                transaction_type="ADJUSTMENT",
                student_id=admin_id,
                data_bytes=0,
                amount_cents=abs(diff),
                debit_account="ADMIN_BUDGET_EQUITY",
                credit_account="ECO_FUND_CASH",
                description=f"{reason} (-{abs(diff)/100:.2f} USD)",
            )

        # Check if any pending donations can now be resolved
        resolved_info = self._attempt_disbursement()

        return {
            "status": "success",
            "previous_balance_usd": round(current_cents / 100.0, 2),
            "new_balance_usd": self.budget_usd,
            "resolved_donations": resolved_info,
        }

    def topup_budget(self, amount_cents: int, admin_id: str = "ADMIN", notes: str = "Cloud savings top-up") -> Dict[str, Any]:
        """Adds funds to the Eco-Fund balance in cents and resolves pending donations."""
        if amount_cents <= 0:
            raise ValueError(f"Top-up amount must be positive, got {amount_cents}")

        self.ledger.append_block(
            transaction_type="BUDGET_TOPUP",
            student_id=admin_id,
            data_bytes=0,
            amount_cents=amount_cents,
            description=notes,
        )

        resolved_info = self._attempt_disbursement()

        return {
            "status": "success",
            "amount_added_usd": round(amount_cents / 100.0, 2),
            "new_balance_usd": self.budget_usd,
            "resolved_donations": resolved_info,
        }

    def accumulate_waste(
        self,
        approved_bytes: int,
        student_id: str = "STU-001",
        student_name: str = "Alex River",
        notes: str = "Verified dark data deletion",
    ) -> Dict[str, Any]:
        """
        Records teacher-approved deleted dark data bytes.
        If cumulative surplus crosses threshold (e.g. 1 GB), executes micro-donation(s).
        Carries over fractional excess bytes cleanly.
        """
        if approved_bytes < 0:
            raise ValueError(f"approved_bytes must be non-negative, got {approved_bytes}")

        # 1. Update cumulative waste
        self.cumulative_waste_bytes += approved_bytes

        # Log data reduction block in ledger if bytes > 0
        if approved_bytes > 0:
            self.ledger.append_block(
                transaction_type="DATA_REDUCTION",
                student_id=student_id,
                data_bytes=approved_bytes,
                amount_cents=0,
                description=f"{notes} ({approved_bytes} bytes by {student_id})",
                metadata={"student_name": student_name, "approved_bytes": approved_bytes},
            )

        # 2. Check surplus
        raw_surplus = self.cumulative_waste_bytes - self.donated_bytes
        trees_to_plant = raw_surplus // self.threshold_bytes if self.threshold_bytes > 0 else 0

        result: Dict[str, Any] = {
            "approved_bytes": approved_bytes,
            "cumulative_waste": self.cumulative_waste_bytes,
            "cumulative_waste_bytes": self.cumulative_waste_bytes,
            "surplus_bytes": raw_surplus,
            "trees_triggered": 0,
            "lifetime_trees": self.lifetime_trees,
            "status": "ACCUMULATING",
            "certificates": [],
            "celebration_event": None,
        }

        if trees_to_plant <= 0:
            return result

        # 3. Check Eco-Fund balance
        total_cost_cents = trees_to_plant * self.cost_per_tree_cents
        available_cents = self.ledger.get_eco_fund_balance_cents()

        if available_cents >= total_cost_cents:
            # Plant trees
            disbursed = self._execute_plant_batch(
                trees_count=trees_to_plant,
                total_cost_cents=total_cost_cents,
                student_id=student_id,
                student_name=student_name,
            )
            self.latest_alert = None
            result.update({
                "status": "DONATION_EXECUTED",
                "trees_triggered": trees_to_plant,
                "lifetime_trees": self.lifetime_trees,
                "cost_usd": round(total_cost_cents / 100.0, 2),
                "cost_cents": total_cost_cents,
                "remaining_budget": self.budget_usd,
                "remaining_budget_usd": self.budget_usd,
                "surplus_bytes": self.surplus_bytes,
                "certificates": disbursed["certificates"],
                "celebration_event": disbursed["celebration_event"],
            })
        else:
            # Budget safety cap: insufficient balance
            self.pending_trees_count += trees_to_plant
            warning_msg = (
                f"Eco-Fund balance (${self.budget_usd:.2f}) is insufficient for "
                f"{trees_to_plant} tree(s) (${total_cost_cents / 100:.2f} needed). "
                f"Donation queued awaiting budget top-up."
            )
            self.latest_alert = {
                "warning": "INSUFFICIENT_ECO_FUND_BUDGET",
                "message": warning_msg,
                "required_cents": total_cost_cents,
                "available_cents": available_cents,
                "deficit_usd": round((total_cost_cents - available_cents) / 100.0, 2),
                "pending_trees": self.pending_trees_count,
            }
            result.update({
                "status": "PENDING_FUNDS",
                "trees_triggered": 0,
                "lifetime_trees": self.lifetime_trees,
                "pending_trees": self.pending_trees_count,
                "alert": self.latest_alert,
                "surplus_bytes": raw_surplus,
            })

        return result

    def _execute_plant_batch(
        self,
        trees_count: int,
        total_cost_cents: int,
        student_id: str,
        student_name: str,
    ) -> Dict[str, Any]:
        """Performs Tree-Nation donation, updates donated bytes, and logs ledger block."""
        # 1. Update donated bytes & lifetime trees
        self.donated_bytes += trees_count * self.threshold_bytes
        self.lifetime_trees += trees_count

        # 2. Call Tree-Nation client
        plant_res = self.tree_client.plant_tree(
            count=trees_count,
            student_id=student_id,
            recipient_name=student_name,
            message=f"Reforestation micro-donation for {trees_count * (self.threshold_bytes // (1024**3))} GB verified Dark Data deleted by {student_name}!",
        )

        cert_url = plant_res.get("certificate_url", f"https://tree-nation.com/certificate/{plant_res.get('tree_id')}")
        species = plant_res.get("species", "Mangrove")
        location = plant_res.get("project_name", "Eden Projects Madagascar")
        coords = plant_res.get("coordinates", {"latitude": -15.7167, "longitude": 46.3167})

        # 3. Record double-entry micro-donation block in ledger
        tx_block = self.ledger.append_block(
            transaction_type="MICRO_DONATION",
            student_id=student_id,
            data_bytes=trees_count * self.threshold_bytes,
            amount_cents=total_cost_cents,
            debit_account="REFORESTATION_EXPENSE",
            credit_account="ECO_FUND_CASH",
            description=f"Planted {trees_count} tree(s) via Reforestation Initiative ({species})",
            metadata={
                "tree_id": plant_res.get("tree_id"),
                "trees_planted": trees_count,
                "species": species,
                "project": location,
                "certificate_url": cert_url,
                "student_name": student_name,
                "co2_offset_kg": plant_res.get("co2_offset_kg", 250.0 * trees_count),
            },
        )

        history_entry = {
            "tx_id": f"tx_{tx_block.block_id:04d}",
            "tree_id": plant_res.get("tree_id"),
            "species": species,
            "co2_offset_kg": plant_res.get("co2_offset_kg", 250.0 * trees_count),
            "certificate_url": cert_url,
            "planted_at": plant_res.get("planted_at"),
            "student_id": student_id,
            "cost_usd": round(total_cost_cents / 100.0, 2),
        }
        self.donations_history.append(history_entry)

        celebration_event = {
            "type": "TREE_PLANTED",
            "trees_count": trees_count,
            "animation": "PARTICLE_BURST_GOLD",
            "sound_cue": "FANFARE",
            "message": f"{trees_count} Tree{'s' if trees_count > 1 else ''} planted!",
            "certificate_url": cert_url,
            "species": species,
            "location": location,
            "coordinates": coords,
        }

        return {
            "certificates": [plant_res],
            "celebration_event": celebration_event,
        }

    def _attempt_disbursement(self) -> Optional[Dict[str, Any]]:
        """Attempts to fund any pending trees when new budget arrives."""
        raw_surplus = self.cumulative_waste_bytes - self.donated_bytes
        trees_needed = raw_surplus // self.threshold_bytes if self.threshold_bytes > 0 else 0

        if trees_needed <= 0:
            return None

        total_cost_cents = trees_needed * self.cost_per_tree_cents
        available_cents = self.ledger.get_eco_fund_balance_cents()

        if available_cents >= total_cost_cents:
            disbursed = self._execute_plant_batch(
                trees_count=trees_needed,
                total_cost_cents=total_cost_cents,
                student_id="STU-RESOLVED",
                student_name="Classroom Eco-Fund",
            )
            self.pending_trees_count = 0
            self.latest_alert = None
            return {
                "trees_planted": trees_needed,
                "cost_usd": round(total_cost_cents / 100.0, 2),
                "remaining_budget_usd": self.budget_usd,
                "celebration_event": disbursed["celebration_event"],
            }
        return None

    def get_status(self) -> Dict[str, Any]:
        """Returns comprehensive Eco-Fund status for student and teacher dashboards."""
        return {
            "budget_usd": self.budget_usd,
            "balance_usd": self.budget_usd,
            "cost_per_tree_usd": self.cost_per_tree_usd,
            "threshold_bytes": self.threshold_bytes,
            "cumulative_waste_bytes": self.cumulative_waste_bytes,
            "donated_bytes": self.donated_bytes,
            "surplus_bytes": self.surplus_bytes,
            "lifetime_trees": self.lifetime_trees,
            "pending_trees": self.pending_trees_count,
            "donations_history": list(self.donations_history),
            "alert": self.latest_alert,
            "is_depleted": self.budget_usd <= 0.0,
            "ledger_verified": self.verify_ledger_integrity(),
        }
