from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from faker import Faker
except ModuleNotFoundError:
    Faker = None

from greenfield_dataset.schema import TABLE_COLUMNS
from greenfield_dataset.state_cache import drop_context_attributes, get_or_build_cache
from greenfield_dataset.settings import GenerationContext
from greenfield_dataset.utils import money, next_id


COST_CENTER_ROWS = [
    ("Executive", None, 1),
    ("Sales", None, 1),
    ("Warehouse", None, 1),
    ("Manufacturing", None, 1),
    ("Purchasing", None, 1),
    ("Administration", None, 1),
    ("Customer Service", None, 1),
    ("Research and Development", None, 1),
    ("Marketing", None, 1),
]

JOB_TITLES_BY_COST_CENTER = {
    "Executive": ["Chief Executive Officer", "Chief Financial Officer", "Controller"],
    "Sales": ["Sales Manager", "Account Executive", "Sales Representative"],
    "Warehouse": ["Warehouse Manager", "Inventory Specialist", "Shipping Clerk"],
    "Manufacturing": [
        "Production Manager",
        "Production Supervisor",
        "Production Planner",
        "Assembler",
        "Machine Operator",
        "Quality Technician",
    ],
    "Purchasing": ["Purchasing Manager", "Buyer", "Procurement Analyst"],
    "Administration": ["Accounting Manager", "Staff Accountant", "Administrative Specialist"],
    "Customer Service": ["Customer Service Manager", "Customer Service Representative"],
    "Research and Development": ["Product Analyst", "Design Coordinator"],
    "Marketing": ["Marketing Manager", "Marketing Specialist"],
}

APPROVAL_LIMITS = {
    "Staff": 0.0,
    "Supervisor": 5000.0,
    "Manager": 25000.0,
    "Executive": 250000.0,
}

ANNUAL_SALARY_BY_LEVEL = {
    "Staff": 54000.0,
    "Supervisor": 78000.0,
    "Manager": 115000.0,
    "Executive": 210000.0,
}

COST_CENTER_SALARY_MULTIPLIERS = {
    "Executive": 1.15,
    "Sales": 1.05,
    "Warehouse": 0.90,
    "Manufacturing": 0.96,
    "Purchasing": 1.00,
    "Administration": 1.00,
    "Customer Service": 0.88,
    "Research and Development": 1.10,
    "Marketing": 1.08,
}

HOURLY_TITLE_RANGES = {
    "Shipping Clerk": (20.0, 26.0),
    "Inventory Specialist": (22.0, 29.0),
    "Assembler": (22.0, 30.0),
    "Machine Operator": (24.0, 32.0),
    "Quality Technician": (25.0, 33.0),
    "Customer Service Representative": (19.0, 25.0),
    "Administrative Specialist": (21.0, 28.0),
}

STANDARD_LABOR_HOURS_RANGE = {
    "Furniture": (1.10, 2.25),
    "Lighting": (0.60, 1.35),
    "Textiles": (0.75, 1.55),
    "Accessories": (0.35, 0.85),
}

STANDARD_LABOR_RATE_RANGE = {
    "Furniture": (26.0, 32.0),
    "Lighting": (24.0, 30.0),
    "Textiles": (23.0, 28.0),
    "Accessories": (22.0, 27.0),
}

VARIABLE_OVERHEAD_RATE_RANGE = {
    "Furniture": (0.32, 0.48),
    "Lighting": (0.28, 0.44),
    "Textiles": (0.26, 0.40),
    "Accessories": (0.22, 0.36),
}

FIXED_OVERHEAD_RATE_RANGE = {
    "Furniture": (0.24, 0.38),
    "Lighting": (0.20, 0.34),
    "Textiles": (0.18, 0.30),
    "Accessories": (0.16, 0.28),
}

ITEM_GROUP_CONFIG = {
    "Furniture": ("FUR", "Finished Good", "Each", "1040", "4010", "5010", (95, 850), (1.65, 2.25)),
    "Lighting": ("LGT", "Finished Good", "Each", "1040", "4020", "5020", (35, 260), (1.75, 2.45)),
    "Textiles": ("TXT", "Finished Good", "Set", "1040", "4030", "5030", (20, 180), (1.80, 2.60)),
    "Accessories": ("ACC", "Finished Good", "Each", "1040", "4040", "5040", (8, 95), (1.90, 2.80)),
    "Packaging": ("PKG", "Purchased Material", "Box", "1045", None, None, (1, 18), None),
    "Raw Materials": ("RAW", "Purchased Material", "Roll", "1045", None, None, (5, 55), None),
}

ACCRUAL_SERVICE_ITEMS = {
    "6100": {
        "ItemCode": "SRV-INS",
        "ItemName": "Insurance Service",
        "StandardCost": 4500.0,
    },
    "6140": {
        "ItemCode": "SRV-SW",
        "ItemName": "IT and Software Service",
        "StandardCost": 6000.0,
    },
    "6180": {
        "ItemCode": "SRV-PRO",
        "ItemName": "Professional Services",
        "StandardCost": 5000.0,
    },
}

MANUFACTURED_SUPPLY_MODE_PROBABILITY = {
    "Furniture": 0.62,
    "Lighting": 0.55,
    "Textiles": 0.28,
    "Accessories": 0.12,
}

PRODUCTION_LEAD_TIME_DAYS = {
    "Furniture": (5, 10),
    "Lighting": (4, 8),
    "Textiles": (3, 7),
    "Accessories": (2, 5),
}

CONVERSION_COST_RATE = {
    "Furniture": (0.22, 0.34),
    "Lighting": (0.18, 0.28),
    "Textiles": (0.14, 0.24),
    "Accessories": (0.10, 0.18),
}

MANUFACTURED_SHARE_TARGET = 0.40
MANUFACTURED_PROMOTION_PRIORITY = {
    "Furniture": 0,
    "Lighting": 1,
    "Textiles": 2,
    "Accessories": 3,
}
MANUFACTURED_DEMOTION_PRIORITY = {
    "Accessories": 0,
    "Textiles": 1,
    "Lighting": 2,
    "Furniture": 3,
}

REGIONS = {
    "Northeast": ["NY", "PA", "NJ", "MA"],
    "Midwest": ["OH", "IN", "MI", "IL", "WI"],
    "South": ["KY", "TN", "GA", "NC", "FL"],
    "West": ["CA", "WA", "OR", "CO", "AZ"],
}

TERMINATION_REASON_OPTIONS = [
    "Resigned",
    "Career Change",
    "Relocated",
    "Performance",
    "Retirement",
]
EMPLOYMENT_CHANGE_PERIOD_LENGTH_DAYS = 14
EMPLOYMENT_CHANGE_PAYDATE_LAG_DAYS = 5

UNIQUE_ACTIVE_ROLE_SPECS = [
    ("Executive", "Chief Executive Officer"),
    ("Executive", "Chief Financial Officer"),
    ("Executive", "Controller"),
    ("Manufacturing", "Production Manager"),
    ("Administration", "Accounting Manager"),
]

CORE_ACTIVE_ROLE_SPECS = [
    ("Sales", "Sales Manager"),
    ("Warehouse", "Warehouse Manager"),
    ("Manufacturing", "Production Supervisor"),
    ("Manufacturing", "Production Planner"),
    ("Purchasing", "Purchasing Manager"),
    ("Customer Service", "Customer Service Manager"),
    ("Marketing", "Marketing Manager"),
    ("Research and Development", "Product Analyst"),
]

REPEATABLE_ROLE_SEQUENCE = [
    ("Sales", "Account Executive"),
    ("Sales", "Sales Representative"),
    ("Warehouse", "Inventory Specialist"),
    ("Warehouse", "Shipping Clerk"),
    ("Manufacturing", "Assembler"),
    ("Manufacturing", "Machine Operator"),
    ("Manufacturing", "Quality Technician"),
    ("Purchasing", "Buyer"),
    ("Purchasing", "Procurement Analyst"),
    ("Administration", "Staff Accountant"),
    ("Administration", "Administrative Specialist"),
    ("Customer Service", "Customer Service Representative"),
    ("Research and Development", "Design Coordinator"),
    ("Marketing", "Marketing Specialist"),
]
CAPACITY_ALIGNMENT_ACTIVE_ROLE_SPECS = [
    ("Manufacturing", "Assembler"),
    ("Manufacturing", "Assembler"),
    ("Manufacturing", "Assembler"),
    ("Manufacturing", "Machine Operator"),
    ("Manufacturing", "Machine Operator"),
    ("Manufacturing", "Quality Technician"),
]
MIN_NON_CAPACITY_ACTIVE_ROLE_COUNT = 1

ROLE_METADATA = {
    "Chief Executive Officer": {
        "AuthorizationLevel": "Executive",
        "JobFamily": "Executive Leadership",
        "JobLevel": "Executive",
    },
    "Chief Financial Officer": {
        "AuthorizationLevel": "Executive",
        "JobFamily": "Executive Leadership",
        "JobLevel": "Executive",
    },
    "Controller": {
        "AuthorizationLevel": "Executive",
        "JobFamily": "Finance and Accounting",
        "JobLevel": "Executive",
    },
    "Production Manager": {
        "AuthorizationLevel": "Manager",
        "JobFamily": "Manufacturing Operations",
        "JobLevel": "Manager",
    },
    "Accounting Manager": {
        "AuthorizationLevel": "Manager",
        "JobFamily": "Finance and Accounting",
        "JobLevel": "Manager",
    },
    "Sales Manager": {
        "AuthorizationLevel": "Manager",
        "JobFamily": "Sales",
        "JobLevel": "Manager",
    },
    "Warehouse Manager": {
        "AuthorizationLevel": "Manager",
        "JobFamily": "Warehouse Operations",
        "JobLevel": "Manager",
    },
    "Production Supervisor": {
        "AuthorizationLevel": "Supervisor",
        "JobFamily": "Manufacturing Operations",
        "JobLevel": "Supervisor",
    },
    "Production Planner": {
        "AuthorizationLevel": "Supervisor",
        "JobFamily": "Manufacturing Operations",
        "JobLevel": "Supervisor",
    },
    "Purchasing Manager": {
        "AuthorizationLevel": "Manager",
        "JobFamily": "Purchasing and Procurement",
        "JobLevel": "Manager",
    },
    "Customer Service Manager": {
        "AuthorizationLevel": "Manager",
        "JobFamily": "Customer Service",
        "JobLevel": "Manager",
    },
    "Marketing Manager": {
        "AuthorizationLevel": "Manager",
        "JobFamily": "Marketing",
        "JobLevel": "Manager",
    },
    "Product Analyst": {
        "AuthorizationLevel": "Staff",
        "JobFamily": "Research and Development",
        "JobLevel": "Professional",
    },
    "Account Executive": {
        "AuthorizationLevel": "Staff",
        "JobFamily": "Sales",
        "JobLevel": "Professional",
    },
    "Sales Representative": {
        "AuthorizationLevel": "Staff",
        "JobFamily": "Sales",
        "JobLevel": "Staff",
    },
    "Inventory Specialist": {
        "AuthorizationLevel": "Staff",
        "JobFamily": "Warehouse Operations",
        "JobLevel": "Staff",
    },
    "Shipping Clerk": {
        "AuthorizationLevel": "Staff",
        "JobFamily": "Warehouse Operations",
        "JobLevel": "Staff",
    },
    "Assembler": {
        "AuthorizationLevel": "Staff",
        "JobFamily": "Manufacturing Operations",
        "JobLevel": "Operator",
    },
    "Machine Operator": {
        "AuthorizationLevel": "Staff",
        "JobFamily": "Manufacturing Operations",
        "JobLevel": "Operator",
    },
    "Quality Technician": {
        "AuthorizationLevel": "Staff",
        "JobFamily": "Manufacturing Operations",
        "JobLevel": "Professional",
    },
    "Buyer": {
        "AuthorizationLevel": "Staff",
        "JobFamily": "Purchasing and Procurement",
        "JobLevel": "Professional",
    },
    "Procurement Analyst": {
        "AuthorizationLevel": "Staff",
        "JobFamily": "Purchasing and Procurement",
        "JobLevel": "Professional",
    },
    "Staff Accountant": {
        "AuthorizationLevel": "Staff",
        "JobFamily": "Finance and Accounting",
        "JobLevel": "Professional",
    },
    "Administrative Specialist": {
        "AuthorizationLevel": "Staff",
        "JobFamily": "Finance and Accounting",
        "JobLevel": "Staff",
    },
    "Customer Service Representative": {
        "AuthorizationLevel": "Staff",
        "JobFamily": "Customer Service",
        "JobLevel": "Staff",
    },
    "Design Coordinator": {
        "AuthorizationLevel": "Staff",
        "JobFamily": "Research and Development",
        "JobLevel": "Professional",
    },
    "Marketing Specialist": {
        "AuthorizationLevel": "Staff",
        "JobFamily": "Marketing",
        "JobLevel": "Professional",
    },
}

WORK_LOCATION_BY_COST_CENTER = {
    "Executive": "Headquarters",
    "Sales": "Headquarters",
    "Warehouse": "East Distribution Center",
    "Manufacturing": "Manufacturing Plant",
    "Purchasing": "Headquarters",
    "Administration": "Headquarters",
    "Customer Service": "Headquarters",
    "Research and Development": "Headquarters",
    "Marketing": "Headquarters",
}

WAREHOUSE_WORK_LOCATIONS = ["East Distribution Center", "West Distribution Center"]

FURNITURE_COLLECTIONS = ["Harbor", "Willow", "Alder", "Summit", "Mason", "Brookside"]
FURNITURE_STYLE_FAMILIES = ["Modern", "Transitional", "Industrial", "Coastal", "Farmhouse"]
FURNITURE_PRODUCTS = [
    ("Dining Table", "TBL"),
    ("Coffee Table", "CTB"),
    ("Bookcase", "BKC"),
    ("Desk", "DSK"),
    ("Console Table", "CON"),
    ("Nightstand", "NGT"),
    ("Bench", "BNH"),
    ("Sideboard", "SDB"),
]
FURNITURE_MATERIALS = ["Oak", "Walnut", "Maple", "Ash", "Acacia"]
FURNITURE_FINISHES = ["Natural", "Warm Walnut", "Matte Black", "Whitewash", "Driftwood"]
FURNITURE_SIZES = ["48 in", "60 in", "72 in", "84 in"]

LIGHTING_COLLECTIONS = ["Beacon", "Atlas", "Solace", "Wren", "Northline", "Crescent"]
LIGHTING_STYLE_FAMILIES = ["Modern", "Minimal", "Classic", "Industrial", "Transitional"]
LIGHTING_PRODUCTS = [
    ("Pendant", "PND"),
    ("Floor Lamp", "FLR"),
    ("Table Lamp", "TBL"),
    ("Wall Sconce", "SCN"),
    ("Chandelier", "CHD"),
]
LIGHTING_MATERIALS = ["Brass", "Steel", "Glass", "Aluminum", "Ceramic"]
LIGHTING_FINISHES = ["Brushed Brass", "Matte Black", "Polished Nickel", "White", "Bronze"]

TEXTILE_COLLECTIONS = ["Loom", "Haven", "Drift", "Ember", "Oakline", "Meadow"]
TEXTILE_STYLE_FAMILIES = ["Textured", "Striped", "Neutral", "Heritage", "Contemporary"]
TEXTILE_PRODUCTS = [
    ("Area Rug", "RUG"),
    ("Throw Blanket", "THR"),
    ("Curtain Panel", "CRT"),
    ("Pillow Cover", "PIL"),
]
TEXTILE_MATERIALS = ["Cotton", "Linen", "Wool Blend", "Poly Blend", "Jute"]
TEXTILE_COLORS = ["Ivory", "Slate", "Sand", "Terracotta", "Sage", "Navy"]
TEXTILE_SIZES = ["Small", "Medium", "Large", "King", "Set of 2"]

ACCESSORY_STYLE_FAMILIES = ["Foundry", "Harbor", "Meadow", "Northline", "Studio"]
ACCESSORY_PRODUCTS = [
    ("Mirror", "MIR"),
    ("Tray", "TRY"),
    ("Planter", "PLN"),
    ("Candle Holder", "CDL"),
    ("Decor Vase", "VAS"),
    ("Wall Art", "ART"),
]
ACCESSORY_MATERIALS = ["Wood", "Metal", "Glass", "Ceramic", "Stone"]
ACCESSORY_FINISHES = ["Natural", "Blackened", "Aged Brass", "Soft White", "Sandstone"]

RAW_MATERIAL_PRODUCTS = [
    ("Oak Veneer", "OVN", "Sheet"),
    ("Walnut Veneer", "WVN", "Sheet"),
    ("Steel Tube", "STL", "Tube"),
    ("Cotton Fabric", "CTN", "Roll"),
    ("Linen Fabric", "LIN", "Roll"),
    ("Brass Hardware", "BRS", "Pack"),
    ("Glass Shade", "GLS", "Case"),
    ("LED Module", "LED", "Pack"),
]

PACKAGING_PRODUCTS = [
    ("Corrugated Carton", "CRT", "Small"),
    ("Foam Insert", "FMI", "Medium"),
    ("Protective Sleeve", "SLV", "Large"),
    ("Label Kit", "LBL", "Pack"),
    ("Inner Box", "BOX", "Medium"),
    ("Pallet Wrap", "PLW", "Large"),
]


class SimpleFaker:
    def __init__(self) -> None:
        self.index = 0

    def seed_instance(self, seed: int) -> None:
        self.index = seed % 1000

    def name(self) -> str:
        self.index += 1
        return f"Employee {self.index:03d}"

    def company(self) -> str:
        self.index += 1
        suffixes = ["LLC", "Inc.", "Company", "Group", "Partners"]
        return f"Greenfield Counterparty {self.index:03d} {suffixes[self.index % len(suffixes)]}"

    def street_address(self) -> str:
        self.index += 1
        return f"{100 + self.index} Market Street"

    def city(self) -> str:
        cities = ["Cincinnati", "Columbus", "Indianapolis", "Louisville", "Pittsburgh"]
        self.index += 1
        return cities[self.index % len(cities)]

    def state_abbr(self) -> str:
        states = ["OH", "IN", "KY", "PA", "MI"]
        self.index += 1
        return states[self.index % len(states)]

    def postcode(self) -> str:
        self.index += 1
        return f"{40000 + self.index:05d}"

    def phone_number(self) -> str:
        self.index += 1
        return f"555-01{self.index % 100:02d}"

    def company_email(self) -> str:
        self.index += 1
        return f"contact{self.index:03d}@example.com"

    def date_between(self, start_date: str, end_date: str) -> pd.Timestamp:
        self.index += 1
        return pd.Timestamp("2018-01-01") + pd.Timedelta(days=self.index % 1800)


def make_faker(seed: int):
    fake = Faker("en_US") if Faker is not None else SimpleFaker()
    fake.seed_instance(seed)
    return fake


def fiscal_start_end(context: GenerationContext) -> tuple[pd.Timestamp, pd.Timestamp]:
    return pd.Timestamp(context.settings.fiscal_year_start), pd.Timestamp(context.settings.fiscal_year_end)


def next_business_day(timestamp: pd.Timestamp) -> pd.Timestamp:
    candidate = pd.Timestamp(timestamp)
    while candidate.day_name() in {"Saturday", "Sunday"}:
        candidate = candidate + pd.Timedelta(days=1)
    return candidate


def payroll_pay_dates(context: GenerationContext) -> list[pd.Timestamp]:
    fiscal_start, fiscal_end = fiscal_start_end(context)
    dates: list[pd.Timestamp] = []
    period_start = fiscal_start
    while period_start <= fiscal_end:
        period_end = min(
            period_start + pd.Timedelta(days=EMPLOYMENT_CHANGE_PERIOD_LENGTH_DAYS - 1),
            fiscal_end,
        )
        pay_date = next_business_day(period_end + pd.Timedelta(days=EMPLOYMENT_CHANGE_PAYDATE_LAG_DAYS))
        dates.append(pay_date)
        period_start = period_end + pd.Timedelta(days=1)
    return dates


def clear_master_data_caches(context: GenerationContext) -> None:
    drop_context_attributes(
        context,
        [
            "_employee_master_cache",
            "_item_master_cache",
            "_current_employee_lookup_cache",
            "_employee_lookup_cache",
            "_employee_valid_ids_by_date_cache",
            "_employee_valid_id_set_by_date_cache",
            "_employee_cost_center_ids_by_date_cache",
            "_employee_title_ids_by_date_cache",
            "_employee_approver_ladder_by_date_cache",
        ],
    )


def employee_master(context: GenerationContext) -> pd.DataFrame:
    def builder() -> pd.DataFrame:
        employees = context.tables["Employee"].copy()
        if employees.empty:
            return employees
        employees["HireDateValue"] = pd.to_datetime(employees["HireDate"])
        employees["TerminationDateValue"] = pd.to_datetime(employees["TerminationDate"], errors="coerce")
        employees["EmployeeIDValue"] = employees["EmployeeID"].astype(int)
        employees["CostCenterIDValue"] = employees["CostCenterID"].astype(int)
        employees["MaxApprovalAmountValue"] = employees["MaxApprovalAmount"].astype(float)
        employees["IsActiveValue"] = employees["IsActive"].astype(int)
        return employees

    return get_or_build_cache(context, "_employee_master_cache", builder)


def item_master(context: GenerationContext) -> pd.DataFrame:
    def builder() -> pd.DataFrame:
        items = context.tables["Item"].copy()
        if items.empty:
            return items
        items["LaunchDateValue"] = pd.to_datetime(items["LaunchDate"], errors="coerce")
        return items

    return get_or_build_cache(context, "_item_master_cache", builder)


def employee_active_mask(employees: pd.DataFrame, event_date: pd.Timestamp | str | None) -> pd.Series:
    if employees.empty:
        return pd.Series(dtype=bool)
    if event_date is None:
        return employees["IsActive"].astype(int).eq(1)
    timestamp = pd.Timestamp(event_date)
    hire_date = employees["HireDateValue"] if "HireDateValue" in employees.columns else pd.to_datetime(employees["HireDate"], errors="coerce")
    termination_date = (
        employees["TerminationDateValue"]
        if "TerminationDateValue" in employees.columns
        else pd.to_datetime(employees["TerminationDate"], errors="coerce")
    )
    return hire_date.le(timestamp) & (termination_date.isna() | termination_date.ge(timestamp))


def _normalized_employee_event_date_key(event_date: pd.Timestamp | str | None) -> str:
    if event_date is None:
        return "__CURRENT__"
    return pd.Timestamp(event_date).normalize().strftime("%Y-%m-%d")


def employee_lookup(context: GenerationContext) -> dict[str, object]:
    def builder() -> dict[str, object]:
        employees = employee_master(context)
        if employees.empty:
            return {
                "all_employee_ids": tuple(),
                "row_index_by_id": {},
                "employee_by_id": {},
                "employee_ids_by_title": {},
                "employee_ids_by_cost_center": {},
                "manager_executive_ids": tuple(),
                "cost_center_name_to_id": {},
            }

        authorization_rank = {"Executive": 0, "Manager": 1, "Supervisor": 2, "Staff": 3}
        sorted_employees = employees.sort_values("EmployeeIDValue").reset_index()
        row_index_by_id: dict[int, int] = {}
        employee_by_id: dict[int, dict[str, object]] = {}
        employee_ids_by_title: dict[str, list[int]] = defaultdict(list)
        employee_ids_by_cost_center: dict[int, list[int]] = defaultdict(list)
        manager_executive_ids: list[int] = []

        for row in sorted_employees.itertuples(index=False):
            employee_id = int(row.EmployeeIDValue)
            cost_center_id = int(row.CostCenterIDValue)
            job_title = str(row.JobTitle)
            authorization_level = str(row.AuthorizationLevel)
            row_index_by_id[employee_id] = int(row.index)
            employee_by_id[employee_id] = {
                "EmployeeID": employee_id,
                "CostCenterID": cost_center_id,
                "JobTitle": job_title,
                "AuthorizationLevel": authorization_level,
                "AuthorizationRank": int(authorization_rank.get(authorization_level, 99)),
                "MaxApprovalAmount": float(row.MaxApprovalAmountValue),
                "IsActive": int(row.IsActiveValue),
                "HireDateValue": pd.Timestamp(row.HireDateValue),
                "TerminationDateValue": None if pd.isna(row.TerminationDateValue) else pd.Timestamp(row.TerminationDateValue),
            }
            employee_ids_by_title[job_title].append(employee_id)
            employee_ids_by_cost_center[cost_center_id].append(employee_id)
            if authorization_level in {"Manager", "Executive"}:
                manager_executive_ids.append(employee_id)

        cost_centers = context.tables["CostCenter"]
        cost_center_name_to_id = {
            str(row.CostCenterName): int(row.CostCenterID)
            for row in cost_centers.itertuples(index=False)
        }
        return {
            "all_employee_ids": tuple(employee_by_id.keys()),
            "row_index_by_id": row_index_by_id,
            "employee_by_id": employee_by_id,
            "employee_ids_by_title": {
                title: tuple(employee_ids)
                for title, employee_ids in employee_ids_by_title.items()
            },
            "employee_ids_by_cost_center": {
                int(cost_center_id): tuple(employee_ids)
                for cost_center_id, employee_ids in employee_ids_by_cost_center.items()
            },
            "manager_executive_ids": tuple(sorted(
                manager_executive_ids,
                key=lambda employee_id: (
                    int(employee_by_id[employee_id]["AuthorizationRank"]),
                    int(employee_id),
                ),
            )),
            "cost_center_name_to_id": cost_center_name_to_id,
        }

    return get_or_build_cache(context, "_employee_lookup_cache", builder)


def _valid_employee_ids_for_date_key(context: GenerationContext, date_key: str) -> tuple[int, ...]:
    cache = get_or_build_cache(context, "_employee_valid_ids_by_date_cache", dict)
    cached = cache.get(date_key)
    if cached is not None:
        return cached

    lookup = employee_lookup(context)
    employee_by_id = lookup["employee_by_id"]
    if date_key == "__CURRENT__":
        valid_ids = tuple(
            employee_id
            for employee_id in lookup["all_employee_ids"]
            if int(employee_by_id[employee_id]["IsActive"]) == 1
        )
    else:
        timestamp = pd.Timestamp(date_key)
        valid_ids = tuple(
            employee_id
            for employee_id in lookup["all_employee_ids"]
            if pd.Timestamp(employee_by_id[employee_id]["HireDateValue"]) <= timestamp
            and (
                employee_by_id[employee_id]["TerminationDateValue"] is None
                or pd.Timestamp(employee_by_id[employee_id]["TerminationDateValue"]) >= timestamp
            )
        )
    cache[date_key] = valid_ids
    return valid_ids


def _valid_employee_id_set_for_date_key(context: GenerationContext, date_key: str) -> set[int]:
    cache = get_or_build_cache(context, "_employee_valid_id_set_by_date_cache", dict)
    cached = cache.get(date_key)
    if cached is not None:
        return cached
    valid_ids = set(_valid_employee_ids_for_date_key(context, date_key))
    cache[date_key] = valid_ids
    return valid_ids


def _employee_ids_for_cost_center_date_key(
    context: GenerationContext,
    date_key: str,
    cost_center_id: int,
) -> tuple[int, ...]:
    cache = get_or_build_cache(context, "_employee_cost_center_ids_by_date_cache", dict)
    cache_key = (date_key, int(cost_center_id))
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    lookup = employee_lookup(context)
    valid_ids = _valid_employee_id_set_for_date_key(context, date_key)
    employee_ids = tuple(
        employee_id
        for employee_id in lookup["employee_ids_by_cost_center"].get(int(cost_center_id), ())
        if employee_id in valid_ids
    )
    cache[cache_key] = employee_ids
    return employee_ids


def _employee_ids_for_title_date_key(
    context: GenerationContext,
    date_key: str,
    job_title: str,
) -> tuple[int, ...]:
    cache = get_or_build_cache(context, "_employee_title_ids_by_date_cache", dict)
    cache_key = (date_key, str(job_title))
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    lookup = employee_lookup(context)
    valid_ids = _valid_employee_id_set_for_date_key(context, date_key)
    employee_ids = tuple(
        employee_id
        for employee_id in lookup["employee_ids_by_title"].get(str(job_title), ())
        if employee_id in valid_ids
    )
    cache[cache_key] = employee_ids
    return employee_ids


def _approver_candidate_ids_for_date_key(context: GenerationContext, date_key: str) -> tuple[int, ...]:
    cache = get_or_build_cache(context, "_employee_approver_ladder_by_date_cache", dict)
    cached = cache.get(date_key)
    if cached is not None:
        return cached

    valid_ids = _valid_employee_id_set_for_date_key(context, date_key)
    lookup = employee_lookup(context)
    approver_ids = tuple(
        employee_id
        for employee_id in lookup["manager_executive_ids"]
        if employee_id in valid_ids
    )
    cache[date_key] = approver_ids
    return approver_ids


def current_active_employees(context: GenerationContext) -> pd.DataFrame:
    _, fiscal_end = fiscal_start_end(context)
    employees = employee_master(context)
    return employees[employee_active_mask(employees, fiscal_end)].copy()


def valid_employees(
    context: GenerationContext,
    event_date: pd.Timestamp | str | None = None,
    *,
    cost_center_id: int | None = None,
    cost_center_name: str | None = None,
    job_titles: list[str] | tuple[str, ...] | None = None,
    authorization_levels: list[str] | tuple[str, ...] | None = None,
    minimum_approval_amount: float | None = None,
) -> pd.DataFrame:
    employees = employee_master(context)
    if employees.empty:
        return employees.copy()

    date_key = _normalized_employee_event_date_key(event_date)
    lookup = employee_lookup(context)
    selected_ids = list(_valid_employee_ids_for_date_key(context, date_key))
    if cost_center_name is not None:
        cost_center_id = lookup["cost_center_name_to_id"].get(str(cost_center_name))
        if cost_center_id is None:
            return employees.head(0).copy()
    if cost_center_id is not None:
        selected_ids = list(_employee_ids_for_cost_center_date_key(context, date_key, int(cost_center_id)))
    if job_titles:
        job_title_ids: set[int] = set()
        for title in job_titles:
            job_title_ids.update(_employee_ids_for_title_date_key(context, date_key, str(title)))
        selected_ids = [employee_id for employee_id in selected_ids if employee_id in job_title_ids]
    if authorization_levels:
        authorization_level_set = {str(level) for level in authorization_levels}
        selected_ids = [
            employee_id
            for employee_id in selected_ids
            if str(lookup["employee_by_id"][employee_id]["AuthorizationLevel"]) in authorization_level_set
        ]
    if minimum_approval_amount is not None:
        minimum_amount = float(minimum_approval_amount)
        selected_ids = [
            employee_id
            for employee_id in selected_ids
            if float(lookup["employee_by_id"][employee_id]["MaxApprovalAmount"]) >= minimum_amount
        ]
    if not selected_ids:
        return employees.head(0).copy()
    row_indexes = [int(lookup["row_index_by_id"][employee_id]) for employee_id in selected_ids]
    return employees.loc[row_indexes].copy()


def employee_ids_for_cost_center_as_of(
    context: GenerationContext,
    cost_center_name_or_id: str | int,
    event_date: pd.Timestamp | str | None = None,
) -> list[int]:
    date_key = _normalized_employee_event_date_key(event_date)
    lookup = employee_lookup(context)
    employee_ids: tuple[int, ...] = tuple()
    if isinstance(cost_center_name_or_id, str):
        cost_center_id = lookup["cost_center_name_to_id"].get(str(cost_center_name_or_id))
        if cost_center_id is not None:
            employee_ids = _employee_ids_for_cost_center_date_key(context, date_key, int(cost_center_id))
    else:
        employee_ids = _employee_ids_for_cost_center_date_key(context, date_key, int(cost_center_name_or_id))
    if employee_ids:
        return list(employee_ids)
    any_valid = _valid_employee_ids_for_date_key(context, date_key)
    if any_valid:
        return list(any_valid)
    return list(lookup["all_employee_ids"])


def employee_id_by_titles(
    context: GenerationContext,
    *job_titles: str,
    event_date: pd.Timestamp | str | None = None,
) -> int | None:
    date_key = _normalized_employee_event_date_key(event_date)
    for title in job_titles:
        employee_ids = _employee_ids_for_title_date_key(context, date_key, str(title))
        if employee_ids:
            return int(employee_ids[0])
    return None


def approver_employee_id(
    context: GenerationContext,
    event_date: pd.Timestamp | str | None = None,
    *,
    preferred_titles: list[str] | tuple[str, ...] | None = None,
    minimum_amount: float = 0.0,
    fallback_cost_center_name: str | None = None,
) -> int:
    date_key = _normalized_employee_event_date_key(event_date)
    lookup = employee_lookup(context)
    employee_by_id = lookup["employee_by_id"]
    minimum_amount_value = float(minimum_amount)
    if preferred_titles:
        for title in preferred_titles:
            preferred_ids = _employee_ids_for_title_date_key(context, date_key, str(title))
            if not preferred_ids:
                continue
            preferred_id = int(preferred_ids[0])
            if minimum_amount_value <= 0 or float(employee_by_id[preferred_id]["MaxApprovalAmount"]) >= minimum_amount_value:
                return preferred_id

    for employee_id in _approver_candidate_ids_for_date_key(context, date_key):
        if float(employee_by_id[employee_id]["MaxApprovalAmount"]) >= minimum_amount_value:
            return int(employee_id)

    if fallback_cost_center_name is not None:
        ids = employee_ids_for_cost_center_as_of(context, fallback_cost_center_name, event_date)
        if ids:
            return int(ids[0])

    any_valid = _valid_employee_ids_for_date_key(context, date_key)
    if any_valid:
        return int(any_valid[0])

    return int(lookup["all_employee_ids"][0])


def current_role_employee_id(context: GenerationContext, *job_titles: str) -> int | None:
    _, fiscal_end = fiscal_start_end(context)
    return employee_id_by_titles(context, *job_titles, event_date=fiscal_end)


def eligible_item_mask(items: pd.DataFrame, event_date: pd.Timestamp | str | None) -> pd.Series:
    if items.empty:
        return pd.Series(dtype=bool)
    if event_date is None:
        return items["IsActive"].astype(int).eq(1)
    timestamp = pd.Timestamp(event_date)
    launch_date = pd.to_datetime(items["LaunchDate"], errors="coerce")
    return items["IsActive"].astype(int).eq(1) & launch_date.notna() & launch_date.le(timestamp)


def eligible_items(context: GenerationContext, event_date: pd.Timestamp | str | None = None) -> pd.DataFrame:
    items = item_master(context)
    return items[eligible_item_mask(items, event_date)].copy()


def account_id_by_number(context: GenerationContext, account_number: str | None) -> int | None:
    if account_number is None:
        return None

    accounts = context.tables["Account"]
    matches = accounts.loc[accounts["AccountNumber"].astype(str) == account_number, "AccountID"]
    if matches.empty:
        raise ValueError(f"Account number {account_number} is not loaded.")
    return int(matches.iloc[0])


def choose(rng, values: list, probabilities: list[float] | None = None):
    if probabilities is None:
        return values[int(rng.integers(0, len(values)))]
    return values[int(rng.choice(len(values), p=probabilities))]


def manufacturing_cost_profile(seed: int, item_group: str) -> dict[str, float]:
    rng = np.random.default_rng(seed)
    labor_hours = money(rng.uniform(*STANDARD_LABOR_HOURS_RANGE[item_group]))
    labor_rate = money(rng.uniform(*STANDARD_LABOR_RATE_RANGE[item_group]))
    direct_labor_cost = money(labor_hours * labor_rate)
    variable_overhead_cost = money(direct_labor_cost * rng.uniform(*VARIABLE_OVERHEAD_RATE_RANGE[item_group]))
    fixed_overhead_cost = money(direct_labor_cost * rng.uniform(*FIXED_OVERHEAD_RATE_RANGE[item_group]))
    standard_conversion_cost = money(direct_labor_cost + variable_overhead_cost + fixed_overhead_cost)
    lead_low, lead_high = PRODUCTION_LEAD_TIME_DAYS[item_group]
    production_lead_time_days = int(rng.integers(lead_low, lead_high + 1))
    return {
        "ProductionLeadTimeDays": production_lead_time_days,
        "StandardLaborHoursPerUnit": labor_hours,
        "StandardDirectLaborCost": direct_labor_cost,
        "StandardVariableOverheadCost": variable_overhead_cost,
        "StandardFixedOverheadCost": fixed_overhead_cost,
        "StandardConversionCost": standard_conversion_cost,
    }


def generate_cost_centers(context: GenerationContext) -> None:
    records = []
    for name, parent_id, is_active in COST_CENTER_ROWS:
        records.append({
            "CostCenterID": next_id(context, "CostCenter"),
            "CostCenterName": name,
            "ParentCostCenterID": parent_id,
            "ManagerID": None,
            "IsActive": is_active,
        })

    context.tables["CostCenter"] = pd.DataFrame(records, columns=TABLE_COLUMNS["CostCenter"])


def load_accounts(context: GenerationContext, accounts_path: str | Path) -> None:
    accounts = pd.read_csv(accounts_path)
    expected = TABLE_COLUMNS["Account"]

    if list(accounts.columns) != expected:
        raise ValueError(f"accounts.csv columns must be exactly: {expected}")

    if accounts["AccountNumber"].duplicated().any():
        duplicates = accounts.loc[accounts["AccountNumber"].duplicated(), "AccountNumber"].tolist()
        raise ValueError(f"Duplicate account numbers: {duplicates}")

    account_ids = set(accounts["AccountID"].astype(int))
    parent_ids = {
        int(parent_id)
        for parent_id in accounts["ParentAccountID"].dropna()
        if str(parent_id).strip() != ""
    }
    missing_parent_ids = sorted(parent_ids - account_ids)
    if missing_parent_ids:
        raise ValueError(f"Account parent IDs do not exist: {missing_parent_ids}")

    accounts["AccountID"] = accounts["AccountID"].astype(int)
    accounts["ParentAccountID"] = accounts["ParentAccountID"].apply(
        lambda value: None if pd.isna(value) or str(value).strip() == "" else int(value)
    )
    accounts["IsActive"] = accounts["IsActive"].astype(int)
    context.tables["Account"] = accounts[expected]
    context.counters["Account"] = int(accounts["AccountID"].max()) + 1


def workforce_target_terminated_count(employee_count: int) -> int:
    minimum = max(1, int(np.ceil(employee_count * 0.08)))
    maximum = max(minimum, int(np.floor(employee_count * 0.15)))
    target = int(round(employee_count * 0.11))
    return max(minimum, min(maximum, target))


def prestart_hire_date(context: GenerationContext, rng: np.random.Generator) -> pd.Timestamp:
    fiscal_start, _ = fiscal_start_end(context)
    lower = fiscal_start - pd.Timedelta(days=365 * 10)
    upper = fiscal_start - pd.Timedelta(days=180)
    span_days = max(int((upper - lower).days), 1)
    return lower + pd.Timedelta(days=int(rng.integers(0, span_days + 1)))


def active_hire_date(context: GenerationContext, rng: np.random.Generator, allow_recent: bool) -> pd.Timestamp:
    fiscal_start, fiscal_end = fiscal_start_end(context)
    if allow_recent and fiscal_end > fiscal_start and float(rng.random()) < 0.22:
        upper = min(fiscal_end - pd.Timedelta(days=30), fiscal_start + pd.Timedelta(days=720))
        if upper > fiscal_start:
            span_days = max(int((upper - fiscal_start).days), 1)
            return fiscal_start + pd.Timedelta(days=int(rng.integers(0, span_days + 1)))
    return prestart_hire_date(context, rng)


def work_location_for_role(cost_center_name: str, position_index: int) -> str:
    if cost_center_name == "Warehouse":
        return WAREHOUSE_WORK_LOCATIONS[position_index % len(WAREHOUSE_WORK_LOCATIONS)]
    return WORK_LOCATION_BY_COST_CENTER.get(cost_center_name, "Headquarters")


def build_employee_role_specs(context: GenerationContext) -> list[dict[str, object]]:
    employee_count = int(context.settings.employee_count)
    base_specs = [
        {"CostCenterName": cost_center_name, "JobTitle": job_title, "Protected": True}
        for cost_center_name, job_title in (UNIQUE_ACTIVE_ROLE_SPECS + CORE_ACTIVE_ROLE_SPECS)
    ]
    desired_capacity_alignment_count = min(
        len(CAPACITY_ALIGNMENT_ACTIVE_ROLE_SPECS),
        max(employee_count - len(base_specs) - MIN_NON_CAPACITY_ACTIVE_ROLE_COUNT, 0),
    )
    terminated_target = workforce_target_terminated_count(employee_count)
    max_pair_count = max((employee_count - len(base_specs) - desired_capacity_alignment_count) // 2, 0)
    terminated_target = min(terminated_target, max_pair_count)
    extra_active_count = max(employee_count - len(base_specs) - (2 * terminated_target), 0)
    capacity_alignment_count = min(extra_active_count, len(CAPACITY_ALIGNMENT_ACTIVE_ROLE_SPECS))

    specs = list(base_specs)
    for index in range(terminated_target):
        cost_center_name, job_title = REPEATABLE_ROLE_SEQUENCE[index % len(REPEATABLE_ROLE_SEQUENCE)]
        specs.append({
            "CostCenterName": cost_center_name,
            "JobTitle": job_title,
            "Protected": False,
            "ReplacementPair": index,
            "IsReplacement": False,
        })
        specs.append({
            "CostCenterName": cost_center_name,
            "JobTitle": job_title,
            "Protected": False,
            "ReplacementPair": index,
            "IsReplacement": True,
        })

    fiscal_start, _ = fiscal_start_end(context)
    for index in range(capacity_alignment_count):
        cost_center_name, job_title = CAPACITY_ALIGNMENT_ACTIVE_ROLE_SPECS[index]
        specs.append({
            "CostCenterName": cost_center_name,
            "JobTitle": job_title,
            "Protected": True,
            "FixedHireDate": fiscal_start.strftime("%Y-%m-%d"),
        })

    for index in range(max(extra_active_count - capacity_alignment_count, 0)):
        cost_center_name, job_title = REPEATABLE_ROLE_SEQUENCE[(terminated_target + index) % len(REPEATABLE_ROLE_SEQUENCE)]
        specs.append({
            "CostCenterName": cost_center_name,
            "JobTitle": job_title,
            "Protected": False,
        })
    return specs[:employee_count]


def generate_employees(context: GenerationContext) -> None:
    fake = make_faker(context.settings.random_seed)
    cost_centers = context.tables["CostCenter"]
    if cost_centers.empty:
        raise ValueError("Generate cost centers before employees.")

    cost_center_ids = cost_centers.set_index("CostCenterName")["CostCenterID"].astype(int).to_dict()
    fiscal_start, fiscal_end = fiscal_start_end(context)
    role_specs = build_employee_role_specs(context)
    if len(role_specs) != int(context.settings.employee_count):
        raise ValueError("Employee role specification count does not match configured employee count.")

    terminated_pair_count = sum(
        1 for spec in role_specs if "ReplacementPair" in spec and not bool(spec.get("IsReplacement"))
    )
    pair_dates: dict[int, dict[str, object]] = {}
    if terminated_pair_count:
        first_valid = fiscal_start + pd.Timedelta(days=45)
        last_valid = max(first_valid, fiscal_end - pd.Timedelta(days=45))
        span_days = max(int((last_valid - first_valid).days), 0)
        eligible_pay_dates = [date for date in payroll_pay_dates(context) if first_valid <= date <= last_valid]
        for pair_index in range(terminated_pair_count):
            rng = np.random.default_rng(context.settings.random_seed + pair_index * 131)
            if eligible_pay_dates:
                base_position = int(round(((len(eligible_pay_dates) - 1) * (pair_index + 1)) / (terminated_pair_count + 1)))
                jitter = int(rng.integers(-1, 2))
                target_position = min(max(base_position + jitter, 0), len(eligible_pay_dates) - 1)
                termination_date = eligible_pay_dates[target_position]
            else:
                base_offset = int(round((span_days * (pair_index + 1)) / (terminated_pair_count + 1))) if span_days else 0
                termination_date = first_valid + pd.Timedelta(days=base_offset + int(rng.integers(-18, 19)))
                termination_date = min(max(termination_date, first_valid), last_valid)
            replacement_hire_date = termination_date + pd.Timedelta(days=int(rng.integers(7, 31)))
            if replacement_hire_date > fiscal_end:
                replacement_hire_date = fiscal_end
                termination_date = min(termination_date, replacement_hire_date - pd.Timedelta(days=1))
            pair_dates[pair_index] = {
                "termination_date": termination_date,
                "replacement_hire_date": replacement_hire_date,
                "termination_reason": TERMINATION_REASON_OPTIONS[pair_index % len(TERMINATION_REASON_OPTIONS)],
            }

    records: list[dict[str, object]] = []
    location_index_by_cost_center: dict[str, int] = {}
    for spec in role_specs:
        employee_id = next_id(context, "Employee")
        cost_center_name = str(spec["CostCenterName"])
        job_title = str(spec["JobTitle"])
        metadata = ROLE_METADATA[job_title]
        rng = np.random.default_rng(context.settings.random_seed + employee_id * 17)
        work_location = work_location_for_role(cost_center_name, location_index_by_cost_center.get(cost_center_name, 0))
        location_index_by_cost_center[cost_center_name] = location_index_by_cost_center.get(cost_center_name, 0) + 1

        employment_status = "Active"
        termination_date = None
        termination_reason = None
        is_active = 1
        if "ReplacementPair" in spec and not bool(spec.get("IsReplacement")):
            pair_info = pair_dates[int(spec["ReplacementPair"])]
            hire_date_value = prestart_hire_date(context, rng)
            termination_date = pd.Timestamp(pair_info["termination_date"])
            termination_reason = str(pair_info["termination_reason"])
            employment_status = "Terminated"
            is_active = 0
        elif "ReplacementPair" in spec and bool(spec.get("IsReplacement")):
            hire_date_value = pd.Timestamp(pair_dates[int(spec["ReplacementPair"])]["replacement_hire_date"])
        elif spec.get("FixedHireDate") is not None:
            hire_date_value = pd.Timestamp(spec["FixedHireDate"])
        else:
            hire_date_value = active_hire_date(context, rng, allow_recent=not bool(spec.get("Protected", False)))

        pay_class = "Hourly" if job_title in HOURLY_TITLE_RANGES else "Salary"
        if pay_class == "Hourly":
            low, high = HOURLY_TITLE_RANGES[job_title]
            base_hourly_rate = money(rng.uniform(low, high))
            base_annual_salary = 0.0
            overtime_eligible = 1
        else:
            base_hourly_rate = 0.0
            multiplier = COST_CENTER_SALARY_MULTIPLIERS.get(cost_center_name, 1.0)
            base_annual_salary = money(
                ANNUAL_SALARY_BY_LEVEL[str(metadata["AuthorizationLevel"])]
                * multiplier
                * rng.uniform(0.96, 1.04)
            )
            overtime_eligible = 0

        records.append({
            "EmployeeID": employee_id,
            "EmployeeName": fake.name(),
            "CostCenterID": int(cost_center_ids[cost_center_name]),
            "JobTitle": job_title,
            "Email": f"employee{employee_id:03d}@greenfield.example",
            "Address": fake.street_address(),
            "City": fake.city(),
            "State": fake.state_abbr(),
            "HireDate": pd.Timestamp(hire_date_value).strftime("%Y-%m-%d"),
            "ManagerID": None,
            "EmployeeNumber": f"EMP-{employee_id:05d}",
            "EmploymentStatus": employment_status,
            "TerminationDate": None if termination_date is None else pd.Timestamp(termination_date).strftime("%Y-%m-%d"),
            "TerminationReason": termination_reason,
            "JobFamily": str(metadata["JobFamily"]),
            "JobLevel": str(metadata["JobLevel"]),
            "WorkLocation": work_location,
            "IsActive": int(is_active),
            "AuthorizationLevel": str(metadata["AuthorizationLevel"]),
            "PayClass": pay_class,
            "BaseHourlyRate": base_hourly_rate,
            "BaseAnnualSalary": base_annual_salary,
            "StandardHoursPerWeek": 40.0,
            "OvertimeEligible": int(overtime_eligible),
            "MaxApprovalAmount": APPROVAL_LIMITS[str(metadata["AuthorizationLevel"])],
        })

    employees = pd.DataFrame(records, columns=TABLE_COLUMNS["Employee"])
    current_employees = employees[employees["IsActive"].astype(int).eq(1)].copy()
    ceo_matches = current_employees.loc[current_employees["JobTitle"].eq("Chief Executive Officer"), "EmployeeID"]
    ceo_id = int(ceo_matches.iloc[0]) if not ceo_matches.empty else int(current_employees.iloc[0]["EmployeeID"])
    manager_by_cost_center = (
        current_employees[current_employees["AuthorizationLevel"].isin(["Manager", "Executive"])]
        .sort_values(["CostCenterID", "EmployeeID"])
        .groupby("CostCenterID")["EmployeeID"]
        .first()
        .to_dict()
    )

    manager_ids: list[int | None] = []
    for row in employees.itertuples(index=False):
        current_manager = manager_by_cost_center.get(int(row.CostCenterID))
        if str(row.JobTitle) == "Chief Executive Officer":
            manager_ids.append(None)
        elif current_manager is not None and int(row.EmployeeID) == int(current_manager):
            manager_ids.append(None if int(row.EmployeeID) == ceo_id else ceo_id)
        else:
            manager_ids.append(int(current_manager) if current_manager is not None else ceo_id)
    employees["ManagerID"] = manager_ids

    context.tables["Employee"] = employees[TABLE_COLUMNS["Employee"]]
    clear_master_data_caches(context)


def backfill_cost_center_managers(context: GenerationContext) -> None:
    cost_centers = context.tables["CostCenter"].copy()
    employees = current_active_employees(context)
    if cost_centers.empty or employees.empty:
        raise ValueError("Generate cost centers and employees before manager backfill.")

    managers = (
        employees[employees["AuthorizationLevel"].isin(["Manager", "Executive"])]
        .groupby("CostCenterID")["EmployeeID"]
        .first()
        .to_dict()
    )
    fallback_managers = employees.sort_values(["CostCenterID", "EmployeeID"]).groupby("CostCenterID")["EmployeeID"].first().to_dict()
    cost_centers["ManagerID"] = cost_centers["CostCenterID"].map(managers)
    cost_centers["ManagerID"] = cost_centers["ManagerID"].fillna(cost_centers["CostCenterID"].map(fallback_managers))
    context.tables["CostCenter"] = cost_centers[TABLE_COLUMNS["CostCenter"]]


def generate_warehouses(context: GenerationContext) -> None:
    fake = make_faker(context.settings.random_seed + 1)

    employees = current_active_employees(context)
    cost_centers = context.tables["CostCenter"]
    if employees.empty:
        raise ValueError("Generate employees before warehouses.")
    if cost_centers.empty:
        raise ValueError("Generate cost centers before warehouses.")

    warehouse_matches = cost_centers.loc[cost_centers["CostCenterName"].eq("Warehouse"), "CostCenterID"]
    warehouse_cost_center_id = int(warehouse_matches.iloc[0]) if not warehouse_matches.empty else None
    warehouse_managers = employees[
        employees["CostCenterID"].eq(warehouse_cost_center_id)
        & employees["AuthorizationLevel"].isin(["Manager", "Executive"])
    ]["EmployeeID"].tolist()
    fallback_manager = int(employees.iloc[0]["EmployeeID"])
    base_names = ["East Distribution Center", "West Distribution Center", "Central Overflow Warehouse"]

    records = []
    for index in range(context.settings.warehouse_count):
        records.append({
            "WarehouseID": next_id(context, "Warehouse"),
            "WarehouseName": base_names[index],
            "Address": fake.street_address(),
            "City": fake.city(),
            "State": fake.state_abbr(),
            "ManagerID": warehouse_managers[index % len(warehouse_managers)]
            if warehouse_managers
            else fallback_manager,
        })

    context.tables["Warehouse"] = pd.DataFrame(records, columns=TABLE_COLUMNS["Warehouse"])


def lifecycle_status_for_finished_good(rng: np.random.Generator) -> str:
    roll = float(rng.random())
    if roll < 0.76:
        return "Core"
    if roll < 0.94:
        return "Seasonal"
    return "Discontinued"


def launch_date_for_lifecycle(
    context: GenerationContext,
    rng: np.random.Generator,
    lifecycle_status: str,
    *,
    allow_in_range_launch: bool = True,
) -> pd.Timestamp:
    fiscal_start, fiscal_end = fiscal_start_end(context)
    if lifecycle_status == "Seasonal" and allow_in_range_launch and float(rng.random()) < 0.55:
        upper = max(fiscal_start, fiscal_end - pd.Timedelta(days=30))
        span_days = max(int((upper - fiscal_start).days), 1)
        return fiscal_start + pd.Timedelta(days=int(rng.integers(0, span_days + 1)))
    if lifecycle_status == "Discontinued":
        lower = fiscal_start - pd.Timedelta(days=365 * 8)
        upper = fiscal_start - pd.Timedelta(days=180)
    else:
        lower = fiscal_start - pd.Timedelta(days=365 * 6)
        upper = fiscal_start - pd.Timedelta(days=30)
    span_days = max(int((upper - lower).days), 1)
    return lower + pd.Timedelta(days=int(rng.integers(0, span_days + 1)))


def finished_good_catalog_attributes(
    context: GenerationContext,
    item_group: str,
    sequence_number: int,
    item_id: int,
) -> dict[str, object]:
    rng = np.random.default_rng(context.settings.random_seed + item_id * 53)
    if item_group == "Furniture":
        collection = FURNITURE_COLLECTIONS[(sequence_number - 1) % len(FURNITURE_COLLECTIONS)]
        style_family = FURNITURE_STYLE_FAMILIES[(sequence_number + 1) % len(FURNITURE_STYLE_FAMILIES)]
        product_name, token = FURNITURE_PRODUCTS[(sequence_number * 3 + item_id) % len(FURNITURE_PRODUCTS)]
        material = FURNITURE_MATERIALS[(sequence_number + item_id) % len(FURNITURE_MATERIALS)]
        finish = FURNITURE_FINISHES[(sequence_number * 2 + item_id) % len(FURNITURE_FINISHES)]
        size = FURNITURE_SIZES[(sequence_number + item_id * 2) % len(FURNITURE_SIZES)]
        return {
            "ItemCode": f"FUR-{token}-{sequence_number:04d}",
            "ItemName": f"{collection} {product_name} {material} {finish} {size}",
            "CollectionName": collection,
            "StyleFamily": style_family,
            "PrimaryMaterial": material,
            "Finish": finish,
            "Color": None,
            "SizeDescriptor": size,
        }
    if item_group == "Lighting":
        collection = LIGHTING_COLLECTIONS[(sequence_number - 1) % len(LIGHTING_COLLECTIONS)]
        style_family = LIGHTING_STYLE_FAMILIES[(sequence_number + 2) % len(LIGHTING_STYLE_FAMILIES)]
        product_name, token = LIGHTING_PRODUCTS[(sequence_number * 5 + item_id) % len(LIGHTING_PRODUCTS)]
        material = LIGHTING_MATERIALS[(sequence_number + item_id) % len(LIGHTING_MATERIALS)]
        finish = LIGHTING_FINISHES[(sequence_number * 2 + item_id) % len(LIGHTING_FINISHES)]
        return {
            "ItemCode": f"LGT-{token}-{sequence_number:04d}",
            "ItemName": f"{collection} {product_name} {finish}",
            "CollectionName": collection,
            "StyleFamily": style_family,
            "PrimaryMaterial": material,
            "Finish": finish,
            "Color": None,
            "SizeDescriptor": None,
        }
    if item_group == "Textiles":
        collection = TEXTILE_COLLECTIONS[(sequence_number - 1) % len(TEXTILE_COLLECTIONS)]
        style_family = TEXTILE_STYLE_FAMILIES[(sequence_number + 1) % len(TEXTILE_STYLE_FAMILIES)]
        product_name, token = TEXTILE_PRODUCTS[(sequence_number * 7 + item_id) % len(TEXTILE_PRODUCTS)]
        material = TEXTILE_MATERIALS[(sequence_number + item_id) % len(TEXTILE_MATERIALS)]
        color = TEXTILE_COLORS[(sequence_number * 2 + item_id) % len(TEXTILE_COLORS)]
        size = TEXTILE_SIZES[(sequence_number + item_id * 3) % len(TEXTILE_SIZES)]
        return {
            "ItemCode": f"TXT-{token}-{sequence_number:04d}",
            "ItemName": f"{collection} {product_name} {color} {size}",
            "CollectionName": collection,
            "StyleFamily": style_family,
            "PrimaryMaterial": material,
            "Finish": None,
            "Color": color,
            "SizeDescriptor": size,
        }
    collection = None
    style_family = ACCESSORY_STYLE_FAMILIES[(sequence_number - 1) % len(ACCESSORY_STYLE_FAMILIES)]
    product_name, token = ACCESSORY_PRODUCTS[(sequence_number * 11 + item_id) % len(ACCESSORY_PRODUCTS)]
    material = ACCESSORY_MATERIALS[(sequence_number + item_id) % len(ACCESSORY_MATERIALS)]
    finish = ACCESSORY_FINISHES[(sequence_number * 2 + item_id) % len(ACCESSORY_FINISHES)]
    return {
        "ItemCode": f"ACC-{token}-{sequence_number:04d}",
        "ItemName": f"{style_family} {product_name} {material} {finish}",
        "CollectionName": collection,
        "StyleFamily": style_family,
        "PrimaryMaterial": material,
        "Finish": finish,
        "Color": None,
        "SizeDescriptor": None,
    }


def material_or_packaging_attributes(item_group: str, sequence_number: int, item_id: int) -> dict[str, object]:
    if item_group == "Raw Materials":
        material_name, token, form = RAW_MATERIAL_PRODUCTS[(sequence_number + item_id) % len(RAW_MATERIAL_PRODUCTS)]
        return {
            "ItemCode": f"RAW-{token}-{sequence_number:04d}",
            "ItemName": f"{material_name} {form}",
            "CollectionName": None,
            "StyleFamily": None,
            "PrimaryMaterial": material_name,
            "Finish": None,
            "Color": None,
            "SizeDescriptor": form,
        }
    descriptor, token, size = PACKAGING_PRODUCTS[(sequence_number + item_id) % len(PACKAGING_PRODUCTS)]
    return {
        "ItemCode": f"PKG-{token}-{sequence_number:04d}",
        "ItemName": f"{descriptor} {size}",
        "CollectionName": None,
        "StyleFamily": None,
        "PrimaryMaterial": descriptor,
        "Finish": None,
        "Color": None,
        "SizeDescriptor": size,
    }


def generate_items(context: GenerationContext) -> None:
    if context.tables["Account"].empty:
        raise ValueError("Load accounts before items.")

    rng = context.rng
    group_names = list(ITEM_GROUP_CONFIG)
    group_probabilities = [0.34, 0.18, 0.17, 0.19, 0.07, 0.05]
    group_counts = {group: 0 for group in group_names}
    records = []

    for _ in range(context.settings.item_count):
        item_group = choose(rng, group_names, group_probabilities)
        group_counts[item_group] += 1
        planned_item_id = context.counters["Item"]
        prefix, item_type, unit, inventory, revenue, cogs, cost_range, markup_range = ITEM_GROUP_CONFIG[item_group]
        standard_cost = money(rng.uniform(*cost_range))
        list_price = None
        supply_mode = "Purchased"
        production_lead_time_days = 0
        standard_labor_hours = 0.0
        standard_direct_labor_cost = 0.0
        standard_variable_overhead_cost = 0.0
        standard_fixed_overhead_cost = 0.0
        standard_conversion_cost = 0.0
        if item_group in {"Furniture", "Lighting", "Textiles", "Accessories"}:
            catalog = finished_good_catalog_attributes(context, item_group, group_counts[item_group], planned_item_id)
            lifecycle_status = lifecycle_status_for_finished_good(rng)
            launch_date = launch_date_for_lifecycle(context, rng, lifecycle_status)
            is_active = 0 if lifecycle_status == "Discontinued" else 1
        else:
            catalog = material_or_packaging_attributes(item_group, group_counts[item_group], planned_item_id)
            lifecycle_status = "Core"
            launch_date = launch_date_for_lifecycle(context, rng, lifecycle_status, allow_in_range_launch=False)
            is_active = 1
        if markup_range is not None:
            if rng.random() <= MANUFACTURED_SUPPLY_MODE_PROBABILITY.get(item_group, 0.0):
                supply_mode = "Manufactured"
                cost_profile = manufacturing_cost_profile(context.settings.random_seed + planned_item_id * 97, item_group)
                production_lead_time_days = int(cost_profile["ProductionLeadTimeDays"])
                standard_labor_hours = float(cost_profile["StandardLaborHoursPerUnit"])
                standard_direct_labor_cost = float(cost_profile["StandardDirectLaborCost"])
                standard_variable_overhead_cost = float(cost_profile["StandardVariableOverheadCost"])
                standard_fixed_overhead_cost = float(cost_profile["StandardFixedOverheadCost"])
                standard_conversion_cost = float(cost_profile["StandardConversionCost"])
            list_price = money(standard_cost * rng.uniform(*markup_range))

        item_id = next_id(context, "Item")
        records.append({
            "ItemID": item_id,
            "ItemCode": str(catalog["ItemCode"]),
            "ItemName": str(catalog["ItemName"]),
            "ItemGroup": item_group,
            "ItemType": item_type,
            "StandardCost": standard_cost,
            "ListPrice": list_price,
            "UnitOfMeasure": unit,
            "SupplyMode": supply_mode,
            "ProductionLeadTimeDays": production_lead_time_days,
            "StandardLaborHoursPerUnit": standard_labor_hours,
            "StandardDirectLaborCost": standard_direct_labor_cost,
            "StandardVariableOverheadCost": standard_variable_overhead_cost,
            "StandardFixedOverheadCost": standard_fixed_overhead_cost,
            "StandardConversionCost": standard_conversion_cost,
            "RoutingID": None,
            "InventoryAccountID": account_id_by_number(context, inventory),
            "RevenueAccountID": account_id_by_number(context, revenue),
            "COGSAccountID": account_id_by_number(context, cogs),
            "PurchaseVarianceAccountID": account_id_by_number(context, "5060"),
            "TaxCategory": "Taxable" if item_group not in ["Packaging", "Raw Materials"] else "Exempt",
            "CollectionName": catalog["CollectionName"],
            "StyleFamily": catalog["StyleFamily"],
            "PrimaryMaterial": catalog["PrimaryMaterial"],
            "Finish": catalog["Finish"],
            "Color": catalog["Color"],
            "SizeDescriptor": catalog["SizeDescriptor"],
            "LifecycleStatus": lifecycle_status,
            "LaunchDate": pd.Timestamp(launch_date).strftime("%Y-%m-%d"),
            "IsActive": int(is_active),
        })

    items = pd.DataFrame(records, columns=TABLE_COLUMNS["Item"])
    sellable_active_mask = items["RevenueAccountID"].notna() & items["IsActive"].eq(1)
    target_manufactured_count = int(round(int(sellable_active_mask.sum()) * MANUFACTURED_SHARE_TARGET))
    manufactured_active_mask = sellable_active_mask & items["SupplyMode"].eq("Manufactured")
    manufactured_count = int(manufactured_active_mask.sum())

    if manufactured_count > target_manufactured_count:
        candidates = items.loc[manufactured_active_mask].copy()
        candidates["Priority"] = candidates["ItemGroup"].map(MANUFACTURED_DEMOTION_PRIORITY).fillna(99)
        candidates = candidates.sort_values(["Priority", "ItemID"], ascending=[True, False])
        demote_count = manufactured_count - target_manufactured_count
        demote_ids = set(candidates.head(demote_count)["ItemID"].astype(int).tolist())
        mask = items["ItemID"].astype(int).isin(demote_ids)
        items.loc[mask, "SupplyMode"] = "Purchased"
        items.loc[mask, "ProductionLeadTimeDays"] = 0
        items.loc[mask, "StandardLaborHoursPerUnit"] = 0.0
        items.loc[mask, "StandardDirectLaborCost"] = 0.0
        items.loc[mask, "StandardVariableOverheadCost"] = 0.0
        items.loc[mask, "StandardFixedOverheadCost"] = 0.0
        items.loc[mask, "StandardConversionCost"] = 0.0
    elif manufactured_count < target_manufactured_count:
        candidates = items.loc[sellable_active_mask & items["SupplyMode"].eq("Purchased")].copy()
        candidates["Priority"] = candidates["ItemGroup"].map(MANUFACTURED_PROMOTION_PRIORITY).fillna(99)
        candidates = candidates.sort_values(["Priority", "ItemID"])
        promote_count = target_manufactured_count - manufactured_count
        promote_ids = candidates.head(promote_count)["ItemID"].astype(int).tolist()
        for item_id in promote_ids:
            row_index = items.index[items["ItemID"].astype(int).eq(int(item_id))][0]
            item_group = str(items.loc[row_index, "ItemGroup"])
            cost_profile = manufacturing_cost_profile(context.settings.random_seed + int(item_id) * 97, item_group)
            items.loc[row_index, "SupplyMode"] = "Manufactured"
            items.loc[row_index, "ProductionLeadTimeDays"] = int(cost_profile["ProductionLeadTimeDays"])
            items.loc[row_index, "StandardLaborHoursPerUnit"] = float(cost_profile["StandardLaborHoursPerUnit"])
            items.loc[row_index, "StandardDirectLaborCost"] = float(cost_profile["StandardDirectLaborCost"])
            items.loc[row_index, "StandardVariableOverheadCost"] = float(cost_profile["StandardVariableOverheadCost"])
            items.loc[row_index, "StandardFixedOverheadCost"] = float(cost_profile["StandardFixedOverheadCost"])
            items.loc[row_index, "StandardConversionCost"] = float(cost_profile["StandardConversionCost"])

    service_rows = []
    for account_number, service_item in ACCRUAL_SERVICE_ITEMS.items():
        launch_date = launch_date_for_lifecycle(context, rng, "Core", allow_in_range_launch=False)
        service_rows.append({
            "ItemID": next_id(context, "Item"),
            "ItemCode": service_item["ItemCode"],
            "ItemName": service_item["ItemName"],
            "ItemGroup": "Services",
            "ItemType": "Service",
            "StandardCost": money(float(service_item["StandardCost"])),
            "ListPrice": None,
            "UnitOfMeasure": "Month",
            "SupplyMode": "Purchased",
            "ProductionLeadTimeDays": 0,
            "StandardLaborHoursPerUnit": 0.0,
            "StandardDirectLaborCost": 0.0,
            "StandardVariableOverheadCost": 0.0,
            "StandardFixedOverheadCost": 0.0,
            "StandardConversionCost": 0.0,
            "RoutingID": None,
            "InventoryAccountID": None,
            "RevenueAccountID": None,
            "COGSAccountID": None,
            "PurchaseVarianceAccountID": account_id_by_number(context, "5060"),
            "TaxCategory": "Exempt",
            "CollectionName": None,
            "StyleFamily": None,
            "PrimaryMaterial": None,
            "Finish": None,
            "Color": None,
            "SizeDescriptor": None,
            "LifecycleStatus": "Core",
            "LaunchDate": pd.Timestamp(launch_date).strftime("%Y-%m-%d"),
            "IsActive": 1,
        })

    if service_rows:
        items = pd.concat([items, pd.DataFrame(service_rows, columns=TABLE_COLUMNS["Item"])], ignore_index=True)

    context.tables["Item"] = items[TABLE_COLUMNS["Item"]]
    clear_master_data_caches(context)


def generate_customers(context: GenerationContext) -> None:
    fake = make_faker(context.settings.random_seed + 2)
    employees = current_active_employees(context)
    cost_centers = context.tables["CostCenter"]
    if employees.empty or cost_centers.empty:
        raise ValueError("Generate employees and cost centers before customers.")

    sales_cost_center_ids = cost_centers.loc[
        cost_centers["CostCenterName"].eq("Sales"),
        "CostCenterID",
    ].tolist()
    sales_reps = employees.loc[
        employees["CostCenterID"].isin(sales_cost_center_ids),
        "EmployeeID",
    ].tolist()
    if not sales_reps:
        sales_reps = employees["EmployeeID"].tolist()

    rng = context.rng
    segments = ["Strategic", "Wholesale", "Design Trade", "Small Business"]
    segment_probabilities = [0.12, 0.38, 0.25, 0.25]
    industries = ["Hospitality", "Retail", "Office", "Real Estate", "Interior Design"]
    terms = ["Net 30", "Net 45", "Net 60", "Net 90"]
    term_probabilities = [0.45, 0.30, 0.20, 0.05]
    records = []

    for index in range(context.settings.customer_count):
        segment = choose(rng, segments, segment_probabilities)
        region = choose(rng, list(REGIONS))
        state = choose(rng, REGIONS[region])
        credit_limit = {
            "Strategic": rng.uniform(125000, 350000),
            "Wholesale": rng.uniform(50000, 175000),
            "Design Trade": rng.uniform(25000, 100000),
            "Small Business": rng.uniform(7500, 40000),
        }[segment]
        customer_id = next_id(context, "Customer")
        records.append({
            "CustomerID": customer_id,
            "CustomerName": fake.company(),
            "ContactName": fake.name(),
            "Address": fake.street_address(),
            "City": fake.city(),
            "State": state,
            "PostalCode": fake.postcode(),
            "Country": "USA",
            "Phone": fake.phone_number(),
            "Email": f"customer{customer_id:04d}@example.com",
            "CreditLimit": money(credit_limit),
            "PaymentTerms": choose(rng, terms, term_probabilities),
            "CustomerSince": fake.date_between(start_date="-10y", end_date="-1y").strftime("%Y-%m-%d"),
            "SalesRepEmployeeID": int(choose(rng, sales_reps)),
            "CustomerSegment": segment,
            "Industry": choose(rng, industries),
            "Region": region,
            "IsActive": 1 if index < int(context.settings.customer_count * 0.96) else 0,
        })

    context.tables["Customer"] = pd.DataFrame(records, columns=TABLE_COLUMNS["Customer"])


def generate_suppliers(context: GenerationContext) -> None:
    fake = make_faker(context.settings.random_seed + 3)
    rng = context.rng
    categories = ["Furniture", "Lighting", "Textiles", "Accessories", "Packaging", "Raw Materials", "Logistics", "Services"]
    category_probabilities = [0.20, 0.13, 0.14, 0.15, 0.10, 0.10, 0.08, 0.10]
    terms = ["Net 30", "Net 45", "Net 60"]
    risk_ratings = ["Low", "Medium", "High"]
    records = []

    for index in range(context.settings.supplier_count):
        supplier_id = next_id(context, "Supplier")
        risk_rating = choose(rng, risk_ratings, [0.68, 0.25, 0.07])
        records.append({
            "SupplierID": supplier_id,
            "SupplierName": fake.company(),
            "ContactName": fake.name(),
            "Address": fake.street_address(),
            "City": fake.city(),
            "State": fake.state_abbr(),
            "PostalCode": fake.postcode(),
            "Country": "USA",
            "Phone": fake.phone_number(),
            "Email": f"supplier{supplier_id:04d}@example.com",
            "PaymentTerms": choose(rng, terms, [0.45, 0.35, 0.20]),
            "IsApproved": 1 if index < int(context.settings.supplier_count * 0.94) else 0,
            "TaxID": f"XX-XXX{1000 + supplier_id:04d}",
            "BankAccount": f"****{5000 + supplier_id:04d}",
            "SupplierCategory": choose(rng, categories, category_probabilities),
            "SupplierRiskRating": risk_rating,
            "DefaultCurrency": "USD",
        })

    context.tables["Supplier"] = pd.DataFrame(records, columns=TABLE_COLUMNS["Supplier"])
