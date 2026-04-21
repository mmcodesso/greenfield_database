from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AccrualAccountSpec:
    account_number: str
    account_name: str
    monthly_base: float

    @property
    def short_name(self) -> str:
        suffix = " Expense"
        if self.account_name.endswith(suffix):
            return self.account_name[: -len(suffix)]
        return self.account_name

    @property
    def description(self) -> str:
        return f"{self.short_name.lower()} accrual"

    @property
    def journal_description(self) -> str:
        return f"Month-end {self.short_name.lower()} accrued expense"

    @property
    def service_item_code(self) -> str:
        return f"SRV-{self.account_number}"

    @property
    def service_item_name(self) -> str:
        return f"{self.short_name} Service"


ACCRUAL_ACCOUNT_SPECS = (
    AccrualAccountSpec("6100", "Insurance Expense", 4500.0),
    AccrualAccountSpec("6110", "Office Supplies Expense", 6500.0),
    AccrualAccountSpec("6120", "Repairs and Maintenance Expense", 10500.0),
    AccrualAccountSpec("6140", "IT and Software Expense", 6000.0),
    AccrualAccountSpec("6150", "Marketing and Promotion Expense", 30000.0),
    AccrualAccountSpec("6160", "Travel and Entertainment Expense", 9500.0),
    AccrualAccountSpec("6180", "Professional Fees Expense", 5000.0),
    AccrualAccountSpec("6190", "Bank Fees Expense", 3500.0),
    AccrualAccountSpec("6200", "Miscellaneous Administrative Expense", 8000.0),
    AccrualAccountSpec("6210", "Warehouse Supplies Expense", 9000.0),
    AccrualAccountSpec("6220", "Research and Development Expense", 24000.0),
)

ACCRUAL_ACCOUNT_NUMBERS = tuple(spec.account_number for spec in ACCRUAL_ACCOUNT_SPECS)

MONTHLY_ACCRUAL_BASES = {
    spec.account_number: float(spec.monthly_base)
    for spec in ACCRUAL_ACCOUNT_SPECS
}

ACCRUAL_ACCOUNT_METADATA = {
    spec.account_number: {
        "account_name": spec.account_name,
        "description": spec.description,
        "journal_description": spec.journal_description,
    }
    for spec in ACCRUAL_ACCOUNT_SPECS
}

ACCRUAL_SERVICE_ITEMS = {
    spec.account_number: {
        "ItemCode": spec.service_item_code,
        "ItemName": spec.service_item_name,
        "StandardCost": float(spec.monthly_base),
    }
    for spec in ACCRUAL_ACCOUNT_SPECS
}
